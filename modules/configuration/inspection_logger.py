from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from .band import Band


class InspectionLogger:

    # Kamera titremesi/geçici gürültü nedeniyle OK<->NG durumu tek bir
    # karede yanlışlıkla değişebilir (aynı fiziksel kasa hareket
    # etmediği halde). Bunu "gerçek" bir değişiklik kabul etmeden önce
    # yeni durumun bu kadar ardışık karede tutarlı kalmasını bekleriz -
    # aksi halde aynı hata birden fazla kez loglanıp bildirilir.
    # Varsayılan; gerçek değer band.confirm_frames'ten okunur ve
    # Debug penceresinden canlı değiştirilebilir (bkz. set_confirm_frames).
    CONFIRM_FRAMES = 3

    def __init__(self, band: Band):

        self.db_path = band.root / "inspection_log.db"

        self.confirm_frames = getattr(
            band, "confirm_frames", self.CONFIRM_FRAMES
        )

        self.last_overall_result = None

        self.pending_result = None
        self.pending_count = 0

        # log() sonrası eklenen satırın id'si (Telegram mesaj
        # eşleştirmesi gibi işlemler için).
        self.last_inserted_id = None

        self._ensure_schema()

    # -------------------------------------------------

    def set_confirm_frames(self, value: int):

        self.confirm_frames = max(1, int(value))

    # -------------------------------------------------
    # Bağlantı
    # -------------------------------------------------
    #
    # WAL modu + synchronous=NORMAL: ani elektrik kesintisi/çökme
    # durumunda veritabanının bozulma riskini büyük ölçüde azaltır,
    # aynı zamanda varsayılan moddan daha hızlı yazma sağlar.
    # synchronous her bağlantıda ayrıca ayarlanmalı çünkü (journal_mode'un
    # aksine) veritabanı dosyasında kalıcı olmuyor, bağlantıya özel.

    def _connect(self) -> sqlite3.Connection:

        conn = sqlite3.connect(self.db_path)

        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")

        return conn

    # -------------------------------------------------

    def _ensure_schema(self):

        conn = self._connect()

        try:

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS inspections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model_name TEXT,
                    overall_result TEXT NOT NULL,
                    roi_results TEXT NOT NULL
                )
                """
            )

            columns = [
                row[1]
                for row in conn.execute(
                    "PRAGMA table_info(inspections)"
                ).fetchall()
            ]

            if "image_path" not in columns:

                conn.execute(
                    "ALTER TABLE inspections ADD COLUMN image_path TEXT"
                )

            if "reviewed" not in columns:

                conn.execute(
                    "ALTER TABLE inspections "
                    "ADD COLUMN reviewed INTEGER NOT NULL DEFAULT 0"
                )

            if "original_result" not in columns:

                conn.execute(
                    "ALTER TABLE inspections ADD COLUMN original_result TEXT"
                )

            if "reviewed_by" not in columns:

                conn.execute(
                    "ALTER TABLE inspections ADD COLUMN reviewed_by TEXT"
                )

            if "telegram_message_id" not in columns:

                conn.execute(
                    "ALTER TABLE inspections "
                    "ADD COLUMN telegram_message_id INTEGER"
                )

            if "training_image_paths" not in columns:

                conn.execute(
                    "ALTER TABLE inspections "
                    "ADD COLUMN training_image_paths TEXT"
                )

            conn.commit()

        finally:

            conn.close()

    # -------------------------------------------------
    # Sonuç Değiştiyse Logla
    # -------------------------------------------------
    #
    # ROI'ler kontrol edilir; hepsi doğruysa (ok) genel durum OK,
    # değilse NG olur. Loglama sadece genel OK/NG durumu bir
    # önceki kareye göre değiştiğinde tetiklenir.

    def should_log(self, results: dict) -> bool:

        if not results:
            return False

        overall_result = self._compute_overall_result(results)

        if overall_result == self.last_overall_result:

            # Zaten kayıtlı durumla aynı - önceden birikmiş yarım kalmış
            # bir "aday değişiklik" varsa (ör. tek karelik bir titreşimdi
            # ve şimdi eski durumuna döndü) onu da iptal et.
            self.pending_result = None
            self.pending_count = 0

            return False

        # İlk hiç kayıt yoksa (last_overall_result None) hemen kabul et -
        # bu bir "titreşim" değil, ilk gözlem. Sonraki gerçek geçişler
        # için ardışık doğrulama bekleriz.
        if self.last_overall_result is None:
            return True

        if overall_result == self.pending_result:
            self.pending_count += 1
        else:
            self.pending_result = overall_result
            self.pending_count = 1

        return self.pending_count >= self.confirm_frames

    def log(
        self,
        results: dict,
        model_name: str | None,
        image_path: str | None = None,
        training_image_paths: dict | None = None
    ) -> bool:
        """
        Kaydı ekler. Eklenen satırın id'si (Telegram mesaj eşleştirmesi
        gibi sonraki işlemler için) self.last_inserted_id'de bulunur.

        training_image_paths (opsiyonel): {roi_name: {"reference": yol,
        "current": yol}} - TrainingDataManager.save() ile diske
        kaydedilmiş ROI görüntü çiftlerinin yolları. Sonradan bir
        düzeltme geldiğinde (correct_roi) bu kayıtlar bulunup
        işaretlenebilsin diye satırla birlikte saklanır.
        """

        if not results:
            return False

        overall_result = self._compute_overall_result(results)

        self.last_overall_result = overall_result

        self.pending_result = None
        self.pending_count = 0

        self._insert(
            overall_result,
            model_name,
            results,
            image_path,
            training_image_paths
        )

        return True

    def log_if_changed(
        self,
        results: dict,
        model_name: str | None,
        image_path: str | None = None,
        training_image_paths: dict | None = None
    ) -> bool:

        if not self.should_log(results):
            return False

        return self.log(
            results, model_name, image_path, training_image_paths
        )

    # -------------------------------------------------

    def _compute_overall_result(self, results: dict) -> str:

        return (
            "OK"
            if all(data["ok"] for data in results.values())
            else "NG"
        )

    # -------------------------------------------------

    def _insert(
        self,
        overall_result,
        model_name,
        results,
        image_path=None,
        training_image_paths=None
    ):

        roi_results = {
            name: {
                "state": data["state"],
                "expected": data["expected"],
                "ok": data["ok"],
                "change_ratio": data["change_ratio"]
            }
            for name, data in results.items()
        }

        conn = self._connect()

        try:

            cursor = conn.execute(
                """
                INSERT INTO inspections
                    (timestamp, model_name, overall_result, roi_results,
                     image_path, training_image_paths)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    model_name,
                    overall_result,
                    json.dumps(roi_results, ensure_ascii=False),
                    image_path,
                    json.dumps(training_image_paths, ensure_ascii=False)
                    if training_image_paths else None
                )
            )

            self.last_inserted_id = cursor.lastrowid

            conn.commit()

        finally:

            conn.close()

    # -------------------------------------------------
    # Son Kayıtları Getir
    # -------------------------------------------------

    def fetch_recent(self, limit: int = 100) -> list:

        conn = self._connect()

        try:

            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                """
                SELECT * FROM inspections
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()

        finally:

            conn.close()

        return [dict(row) for row in rows]

    # -------------------------------------------------
    # İstatistikler
    # -------------------------------------------------

    def compute_stats(self) -> dict:

        conn = self._connect()

        try:

            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                "SELECT model_name, overall_result, roi_results "
                "FROM inspections"
            ).fetchall()

        finally:

            conn.close()

        return self._aggregate_rows(rows)

    # -------------------------------------------------
    # Belirli Bir Tarihten Sonraki İstatistikler
    # -------------------------------------------------
    #
    # Periyodik (günlük) Telegram özet raporu için kullanılır -
    # compute_stats()'in tüm zamanlar yerine sadece since_iso'dan
    # sonraki kayıtlara bakan hali.

    def compute_period_stats(self, since_iso: str) -> dict:

        conn = self._connect()

        try:

            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                "SELECT model_name, overall_result, roi_results "
                "FROM inspections WHERE timestamp >= ?",
                (since_iso,)
            ).fetchall()

        finally:

            conn.close()

        return self._aggregate_rows(rows)

    # -------------------------------------------------

    def _aggregate_rows(self, rows) -> dict:

        total = len(rows)
        ok_count = 0
        ng_count = 0
        by_model = {}
        by_roi = {}

        for row in rows:

            is_ok = row["overall_result"] == "OK"

            if is_ok:
                ok_count += 1
            else:
                ng_count += 1

            model_name = row["model_name"] or "-"

            model_stats = by_model.setdefault(
                model_name,
                {"ok": 0, "ng": 0}
            )

            model_stats["ok" if is_ok else "ng"] += 1

            try:
                roi_results = json.loads(row["roi_results"])
            except Exception:
                roi_results = {}

            for roi_name, data in roi_results.items():

                roi_stats = by_roi.setdefault(
                    roi_name,
                    {"ok": 0, "ng": 0}
                )

                roi_stats["ok" if data.get("ok") else "ng"] += 1

        return {
            "total": total,
            "ok_count": ok_count,
            "ng_count": ng_count,
            "by_model": by_model,
            "by_roi": by_roi
        }

    # -------------------------------------------------
    # Günlük NG Oranı Trendi
    # -------------------------------------------------

    def compute_daily_trend(self, limit_days: int = 30) -> list:

        conn = self._connect()

        try:

            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                "SELECT timestamp, overall_result FROM inspections "
                "ORDER BY id"
            ).fetchall()

        finally:

            conn.close()

        daily = {}

        for row in rows:

            try:
                local_dt = datetime.fromisoformat(row["timestamp"]).astimezone()
            except Exception:
                continue

            date_key = local_dt.strftime("%Y-%m-%d")

            day_stats = daily.setdefault(date_key, {"ok": 0, "ng": 0})

            if row["overall_result"] == "OK":
                day_stats["ok"] += 1
            else:
                day_stats["ng"] += 1

        dates = sorted(daily.keys())[-limit_days:]

        trend = []

        for date_key in dates:

            day_stats = daily[date_key]

            total = day_stats["ok"] + day_stats["ng"]

            ratio = (day_stats["ng"] / total * 100) if total else 0.0

            trend.append({
                "date": date_key,
                "total": total,
                "ok": day_stats["ok"],
                "ng": day_stats["ng"],
                "ng_ratio": ratio
            })

        return trend

    # -------------------------------------------------
    # Vardiya Bazlı NG Oranı Trendi
    # -------------------------------------------------
    #
    # Bandın tanımlı vardiya pencereleri (bkz. Band.shifts,
    # ShiftSettingsPanel) sabit saat aralıklarıdır (ör. "Sabah"
    # 07:30-15:30). Geçmiş vardiyaların ne zaman başladığı ayrıca
    # saklanmaz - her kaydın yerel saati, tanımlı pencerelerden
    # hangisine düşüyorsa ona göre HESAPLANIR. Hiçbir pencereye
    # düşmeyen kayıtlar (mesai dışı üretim) trende dahil edilmez -
    # bu artık sadece tanımlı vardiyaların NG oranını gösterir.

    def compute_shift_trend(
        self,
        shifts: list,
        limit_shifts: int = 20
    ) -> list:

        parsed_shifts = []

        for shift in shifts:

            try:
                start_t = datetime.strptime(shift.start, "%H:%M").time()
                end_t = datetime.strptime(shift.end, "%H:%M").time()
            except (ValueError, AttributeError):
                continue

            parsed_shifts.append(
                (shift.name, start_t, end_t, end_t <= start_t)
            )

        if not parsed_shifts:
            return []

        conn = self._connect()

        try:

            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                "SELECT timestamp, overall_result FROM inspections "
                "ORDER BY id"
            ).fetchall()

        finally:

            conn.close()

        buckets = {}

        for row in rows:

            try:
                local_dt = datetime.fromisoformat(row["timestamp"]).astimezone()
            except Exception:
                continue

            day = local_dt.date()

            for name, start_t, end_t, overnight in parsed_shifts:

                window_start = datetime.combine(
                    day, start_t, tzinfo=local_dt.tzinfo
                )
                window_end = datetime.combine(
                    day, end_t, tzinfo=local_dt.tzinfo
                )

                if overnight:
                    window_end += timedelta(days=1)

                if local_dt < window_start and overnight:
                    window_start -= timedelta(days=1)
                    window_end -= timedelta(days=1)

                if not (window_start <= local_dt < window_end):
                    continue

                bucket_key = (name, window_start.isoformat())

                bucket_stats = buckets.setdefault(
                    bucket_key,
                    {"name": name, "start": window_start, "ok": 0, "ng": 0}
                )

                if row["overall_result"] == "OK":
                    bucket_stats["ok"] += 1
                else:
                    bucket_stats["ng"] += 1

                break

        bucket_keys = sorted(
            buckets.keys(), key=lambda key: buckets[key]["start"]
        )[-limit_shifts:]

        trend = []

        for bucket_key in bucket_keys:

            bucket_stats = buckets[bucket_key]

            total = bucket_stats["ok"] + bucket_stats["ng"]

            ratio = (bucket_stats["ng"] / total * 100) if total else 0.0

            trend.append({
                "date": (
                    f"{bucket_stats['start'].strftime('%Y-%m-%d %H:%M')} "
                    f"{bucket_stats['name']}"
                ),
                "total": total,
                "ok": bucket_stats["ok"],
                "ng": bucket_stats["ng"],
                "ng_ratio": ratio
            })

        return trend

    # -------------------------------------------------
    # Telegram Mesaj Eşleştirmesi
    # -------------------------------------------------
    #
    # Bir NG bildirimi Telegram'a gönderildiğinde dönen mesaj id'si
    # burada saklanır. Kullanıcı o mesaja onay emojisiyle tepki
    # verdiğinde, mesaj id'sinden hangi kaydın düzeltileceği bulunur.

    def set_telegram_message_id(self, record_id: int, message_id: int):

        conn = self._connect()

        try:

            conn.execute(
                "UPDATE inspections SET telegram_message_id = ? "
                "WHERE id = ?",
                (message_id, record_id)
            )

            conn.commit()

        finally:

            conn.close()

    def find_record_by_telegram_message_id(self, message_id: int):

        conn = self._connect()

        try:

            row = conn.execute(
                "SELECT id FROM inspections "
                "WHERE telegram_message_id = ? "
                "ORDER BY id DESC LIMIT 1",
                (message_id,)
            ).fetchone()

        finally:

            conn.close()

        return row[0] if row is not None else None

    # -------------------------------------------------
    # Eğitim Verisi Görüntü Yolları
    # -------------------------------------------------

    def get_training_image_paths(self, record_id: int) -> dict:
        """
        log() sırasında kaydedilmişse, {roi_name: {"reference": yol,
        "current": yol}} döner. Kayıt yoksa ya da o an için eğitim
        verisi kaydedilmemişse boş sözlük döner.
        """

        conn = self._connect()

        try:

            row = conn.execute(
                "SELECT training_image_paths FROM inspections WHERE id = ?",
                (record_id,)
            ).fetchone()

        finally:

            conn.close()

        if row is None or row[0] is None:
            return {}

        try:
            return json.loads(row[0])
        except Exception:
            return {}

    # -------------------------------------------------
    # NG Kaydını İncelenmiş Olarak OK'e Çevir
    # -------------------------------------------------

    def mark_reviewed_ok(
        self,
        record_id: int,
        operator_name: str | None = None
    ) -> bool:

        conn = self._connect()

        try:

            row = conn.execute(
                "SELECT overall_result, original_result "
                "FROM inspections WHERE id = ?",
                (record_id,)
            ).fetchone()

            if row is None:
                return False

            current_result, original_result = row

            if original_result is None:
                original_result = current_result

            conn.execute(
                """
                UPDATE inspections
                SET overall_result = 'OK',
                    reviewed = 1,
                    original_result = ?,
                    reviewed_by = ?
                WHERE id = ?
                """,
                (original_result, operator_name, record_id)
            )

            conn.commit()

        finally:

            conn.close()

        return True

    # -------------------------------------------------
    # Tek Bir ROI'yi Düzelt
    # -------------------------------------------------
    #
    # Belirli bir ROI yanlış tespit edilmiş olabilir (örn. dolu
    # bir göz boş görülmüş). Bu ROI'nin "ok" değeri düzeltilir,
    # orijinal tespit (model eğitimi için) roi_results içinde
    # "original_ok" olarak saklanır, ve genel sonuç güncel ROI
    # durumlarına göre yeniden hesaplanır.

    def correct_roi(
        self,
        record_id: int,
        roi_name: str,
        corrected_ok: bool = True,
        operator_name: str | None = None
    ) -> bool:

        conn = self._connect()

        try:

            row = conn.execute(
                "SELECT roi_results, overall_result, original_result "
                "FROM inspections WHERE id = ?",
                (record_id,)
            ).fetchone()

            if row is None:
                return False

            roi_results_json, current_result, original_result = row

            roi_results = json.loads(roi_results_json)

            if roi_name not in roi_results:
                return False

            roi_data = roi_results[roi_name]

            if "original_ok" not in roi_data:
                roi_data["original_ok"] = roi_data["ok"]

            roi_data["ok"] = corrected_ok
            roi_data["reviewed"] = True

            new_overall_result = (
                "OK"
                if all(data["ok"] for data in roi_results.values())
                else "NG"
            )

            if original_result is None:
                original_result = current_result

            conn.execute(
                """
                UPDATE inspections
                SET roi_results = ?,
                    overall_result = ?,
                    reviewed = 1,
                    original_result = ?,
                    reviewed_by = ?
                WHERE id = ?
                """,
                (
                    json.dumps(roi_results, ensure_ascii=False),
                    new_overall_result,
                    original_result,
                    operator_name,
                    record_id
                )
            )

            conn.commit()

        finally:

            conn.close()

        return True

    # -------------------------------------------------
    # Geçmişi Temizle
    # -------------------------------------------------

    def clear(self):

        conn = self._connect()

        try:

            conn.execute("DELETE FROM inspections")

            conn.commit()

        finally:

            conn.close()

        self.last_overall_result = None
