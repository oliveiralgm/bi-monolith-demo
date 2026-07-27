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
            user_agent TEXT,
            visitor_kind TEXT,
            client_ip TEXT
        )
        """
    )
    cols = {row[1] for row in conn.execute("PRAGMA table_info(page_loads)")}
    if "visitor_kind" not in cols:
        conn.execute("ALTER TABLE page_loads ADD COLUMN visitor_kind TEXT")
    if "client_ip" not in cols:
        conn.execute("ALTER TABLE page_loads ADD COLUMN client_ip TEXT")
    conn.commit()
    return conn


def record_page_load(
    path: str,
    dashboard_slug: str | None = None,
    user_agent: str | None = None,
    visitor_kind: str | None = None,
    client_ip: str | None = None,
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    kind = (visitor_kind or "other").strip().lower()
    if kind not in {"self", "other"}:
        kind = "other"
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO page_loads
                    (ts_utc, path, dashboard_slug, user_agent, visitor_kind, client_ip)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    path,
                    dashboard_slug,
                    (user_agent or "")[:240],
                    kind,
                    (client_ip or "")[:64],
                ),
            )
            conn.commit()
        finally:
            conn.close()


def _by_dashboard(conn: sqlite3.Connection, kind: str | None = None) -> List[Dict[str, Any]]:
    if kind == "self":
        rows = conn.execute(
            """
            SELECT COALESCE(dashboard_slug, '(home)') AS dashboard_slug, COUNT(*) AS n
            FROM page_loads
            WHERE COALESCE(visitor_kind, 'other') = 'self'
            GROUP BY 1
            ORDER BY n DESC
            """
        )
    elif kind == "other":
        rows = conn.execute(
            """
            SELECT COALESCE(dashboard_slug, '(home)') AS dashboard_slug, COUNT(*) AS n
            FROM page_loads
            WHERE COALESCE(visitor_kind, 'other') != 'self'
            GROUP BY 1
            ORDER BY n DESC
            """
        )
    else:
        rows = conn.execute(
            """
            SELECT COALESCE(dashboard_slug, '(home)') AS dashboard_slug, COUNT(*) AS n
            FROM page_loads
            GROUP BY 1
            ORDER BY n DESC
            """
        )
    return [{"dashboard": r["dashboard_slug"] or "(home)", "loads": r["n"]} for r in rows]


def summary_stats(days: int = 30) -> Dict[str, Any]:
    """Aggregate stub metrics for the adoption dashboard."""
    with _LOCK:
        conn = _connect()
        try:
            conn.row_factory = sqlite3.Row
            total = conn.execute("SELECT COUNT(*) AS n FROM page_loads").fetchone()["n"]
            self_n = conn.execute(
                "SELECT COUNT(*) AS n FROM page_loads WHERE COALESCE(visitor_kind, 'other') = 'self'"
            ).fetchone()["n"]
            other_n = conn.execute(
                "SELECT COUNT(*) AS n FROM page_loads WHERE COALESCE(visitor_kind, 'other') != 'self'"
            ).fetchone()["n"]

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

            recent = [
                {
                    "ts": r["ts_utc"],
                    "path": r["path"],
                    "kind": r["visitor_kind"] or "other",
                    "ip": r["client_ip"] or "",
                }
                for r in conn.execute(
                    """
                    SELECT ts_utc, path, visitor_kind, client_ip
                    FROM page_loads
                    ORDER BY id DESC
                    LIMIT 12
                    """
                )
            ]

            distinct_other_ips = [
                r["client_ip"]
                for r in conn.execute(
                    """
                    SELECT DISTINCT client_ip
                    FROM page_loads
                    WHERE COALESCE(visitor_kind, 'other') != 'self'
                      AND client_ip IS NOT NULL
                      AND client_ip != ''
                    ORDER BY client_ip
                    LIMIT 8
                    """
                )
            ]

            return {
                "total_loads": total,
                "self_loads": self_n,
                "other_loads": other_n,
                "by_dashboard": _by_dashboard(conn),
                "by_dashboard_self": _by_dashboard(conn, "self"),
                "by_dashboard_other": _by_dashboard(conn, "other"),
                "by_day": by_day,
                "recent": recent,
                "other_ips": distinct_other_ips,
            }
        finally:
            conn.close()
