"""Tiny page-load telemetry stub (local sqlite). Not a warehouse pipeline."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

_DB_PATH = Path(__file__).resolve().parent / "data" / "telemetry.sqlite"
_LOCK = threading.Lock()


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS page_loads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc TEXT NOT NULL,
            path TEXT NOT NULL,
            dashboard_slug TEXT,
            user_agent TEXT
        )
        """
    )
    conn.commit()
    return conn


def record_page_load(path: str, dashboard_slug: str | None = None, user_agent: str | None = None) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO page_loads (ts_utc, path, dashboard_slug, user_agent) VALUES (?, ?, ?, ?)",
                (ts, path, dashboard_slug, (user_agent or "")[:240]),
            )
            conn.commit()
        finally:
            conn.close()


def summary_stats(days: int = 30) -> Dict[str, Any]:
    """Aggregate stub metrics for the adoption dashboard."""
    with _LOCK:
        conn = _connect()
        try:
            conn.row_factory = sqlite3.Row
            total = conn.execute("SELECT COUNT(*) AS n FROM page_loads").fetchone()["n"]
            by_dash: List[Dict[str, Any]] = [
                {"dashboard": r["dashboard_slug"] or "(home)", "loads": r["n"]}
                for r in conn.execute(
                    """
                    SELECT COALESCE(dashboard_slug, '(home)') AS dashboard_slug, COUNT(*) AS n
                    FROM page_loads
                    GROUP BY 1
                    ORDER BY n DESC
                    """
                )
            ]
            by_day = [
                {"day": r["day"], "loads": r["n"]}
                for r in conn.execute(
                    """
                    SELECT substr(ts_utc, 1, 10) AS day, COUNT(*) AS n
                    FROM page_loads
                    GROUP BY 1
                    ORDER BY 1 DESC
                    LIMIT ?
                    """,
                    (days,),
                )
            ]
            by_day.reverse()
            return {"total_loads": total, "by_dashboard": by_dash, "by_day": by_day}
        finally:
            conn.close()
