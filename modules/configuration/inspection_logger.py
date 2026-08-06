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
        image_path: str | None = None
    ) -> bool:
        """
        Kaydı ekler. Eklenen satırın id'si (Telegram mesaj eşleştirmesi
        gibi sonraki işlemler için) self.last_inserted_id'de bulunur.
        """

        if not results:
            return False

        overall_result = self._compute_overall_result(results)

        self.last_overall_result = overall_result

        self.pending_result = None
        self.pending_count = 0

        self._insert(overall_result, model_name, results, image_path)

        return True

    def log_if_changed(
        self,
        results: dict,
        model_name: str | None,
        image_path: str | None = None
    ) -> bool:

        if not self.should_log(results):
            return False

        return self.log(results, model_name, image_path)

    # -------------------------------------------------

    def _compute_overall_result(self, results: dict) -> str:

        return (
            "OK"
            if all(data["ok"] for data in results.values())
            else "NG"
        )

    # -------------------------------------------------

    def _insert(self, overall_result, model_name, results, image_path=None):

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
                    (timestamp, model_name, overall_result, roi_results, image_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    model_name,
                    overall_result,
                    json.dumps(roi_results, ensure_ascii=False),
                    image_path
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
    # Geçmiş vardiyaların ne zaman başladığı hiçbir yerde
    # saklanmıyor (InspectionUIController.shift_start_time sadece
    # o an çalışan oturum için bellekte tutulur, kalıcı değildir).
    # Bu yüzden vardiya sınırları, gece yarısından başlayarak
    # shift_duration_hours'a göre HESAPLANIR (ör. 8 saatlik
    # vardiyalarda 00:00-08:00 / 08:00-16:00 / 16:00-24:00) -
    # klasik 3 vardiyalı üretim düzenine denk gelir ve yeni bir
    # kalıcı depolamaya ihtiyaç duymadan geçmişe dönük hesaplanabilir.

    def compute_shift_trend(
        self,
        shift_duration_hours: float,
        limit_shifts: int = 20
    ) -> list:

        if shift_duration_hours <= 0:
            shift_duration_hours = 8.0

        conn = self._connect()

        try:

            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                "SELECT timestamp, overall_result FROM inspections "
                "ORDER BY id"
            ).fetchall()

        finally:

            conn.close()

        shifts = {}

        for row in rows:

            try:
                local_dt = datetime.fromisoformat(row["timestamp"]).astimezone()
            except Exception:
                continue

            day_start = local_dt.replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            hours_since_midnight = (
                (local_dt - day_start).total_seconds() / 3600
            )

            shift_index = int(hours_since_midnight // shift_duration_hours)

            shift_start = day_start + timedelta(
                hours=shift_index * shift_duration_hours
            )

            shift_key = shift_start.isoformat()

            shift_stats = shifts.setdefault(
                shift_key, {"start": shift_start, "ok": 0, "ng": 0}
            )

            if row["overall_result"] == "OK":
                shift_stats["ok"] += 1
            else:
                shift_stats["ng"] += 1

        shift_keys = sorted(shifts.keys())[-limit_shifts:]

        trend = []

        for shift_key in shift_keys:

            shift_stats = shifts[shift_key]

            total = shift_stats["ok"] + shift_stats["ng"]

            ratio = (shift_stats["ng"] / total * 100) if total else 0.0

            trend.append({
                "date": shift_stats["start"].strftime("%Y-%m-%d %H:%M"),
                "total": total,
                "ok": shift_stats["ok"],
                "ng": shift_stats["ng"],
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
