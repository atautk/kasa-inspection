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

    def _ensure_schema(self):

        conn = sqlite3.connect(self.db_path)

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

            conn.commit()

        finally:

            conn.close()

    # -------------------------------------------------
    # Sonuç Değiştiyse Logla
    # -------------------------------------------------

    def log_if_changed(
        self,
        results: dict,
        model_name: str | None,
        image_path: str | None = None
    ) -> bool:

        if not results:
            return False

        overall_result = (
            "OK"
            if all(data["ok"] for data in results.values())
            else "NG"
        )

        if overall_result == self.last_overall_result:
            return False

        self.last_overall_result = overall_result

        self._insert(overall_result, model_name, results, image_path)

        return True

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

        conn = sqlite3.connect(self.db_path)

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

        conn = sqlite3.connect(self.db_path)

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

        conn = sqlite3.connect(self.db_path)

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
    # Geçmişi Temizle
    # -------------------------------------------------

    def clear(self):

        conn = sqlite3.connect(self.db_path)

        try:

            conn.execute("DELETE FROM inspections")

            conn.commit()

        finally:

            conn.close()

        self.last_overall_result = None
