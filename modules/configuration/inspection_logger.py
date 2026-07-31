from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from .band import Band


class InspectionLogger:

    def __init__(self, band: Band):

        self.db_path = band.root / "inspection_log.db"

        self.last_overall_result = None

        self._ensure_schema()

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

        return overall_result != self.last_overall_result

    def log(
        self,
        results: dict,
        model_name: str | None,
        image_path: str | None = None
    ) -> bool:

        if not results:
            return False

        overall_result = self._compute_overall_result(results)

        self.last_overall_result = overall_result

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

            conn.execute(
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
