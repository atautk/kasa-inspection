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
