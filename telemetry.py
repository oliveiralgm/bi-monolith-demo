"""Tiny page-load telemetry stub (local sqlite). Not a warehouse pipeline."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

_DB_PATH = Path(__file__).resolve().parent / "data" / "telemetry.sqlite"
_LOCK = threading.Lock()


ROLE_CHOICES = (
    "Recruiter",
    "Hiring manager",
    "Engineer",
    "Analyst",
    "Other",
    "Prefer not to say",
)
FOUND_CHOICES = ("Resume", "GitHub", "Referral", "Other")


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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visitor_intros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc TEXT NOT NULL,
            company TEXT,
            role TEXT,
            found_via TEXT,
            skipped INTEGER NOT NULL DEFAULT 0,
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
                "visitor_intros": _visitor_intro_stats(conn),
            }
        finally:
            conn.close()


def record_visitor_intro(
    company: str | None = None,
    role: str | None = None,
    found_via: str | None = None,
    skipped: bool = False,
    visitor_kind: str | None = None,
    client_ip: str | None = None,
) -> None:
    """Store an optional who-are-you answer (or an explicit skip)."""
    ts = datetime.now(timezone.utc).isoformat()
    kind = (visitor_kind or "other").strip().lower()
    if kind not in {"self", "other"}:
        kind = "other"

    company_clean = (company or "").strip()[:120]
    role_clean = (role or "").strip()[:64]
    found_clean = (found_via or "").strip()[:64]
    if role_clean and role_clean not in ROLE_CHOICES:
        role_clean = "Other"
    if found_clean and found_clean not in FOUND_CHOICES:
        found_clean = "Other"

    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO visitor_intros
                    (ts_utc, company, role, found_via, skipped, visitor_kind, client_ip)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    company_clean or None,
                    None if skipped else (role_clean or None),
                    None if skipped else (found_clean or None),
                    1 if skipped else 0,
                    kind,
                    (client_ip or "")[:64],
                ),
            )
            conn.commit()
        finally:
            conn.close()


def _visitor_intro_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    answered = conn.execute(
        "SELECT COUNT(*) AS n FROM visitor_intros WHERE skipped = 0"
    ).fetchone()["n"]
    skipped_n = conn.execute(
        "SELECT COUNT(*) AS n FROM visitor_intros WHERE skipped = 1"
    ).fetchone()["n"]

    by_role = [
        {"role": r["role"] or "(blank)", "n": r["n"]}
        for r in conn.execute(
            """
            SELECT COALESCE(NULLIF(TRIM(role), ''), '(blank)') AS role, COUNT(*) AS n
            FROM visitor_intros
            WHERE skipped = 0
            GROUP BY 1
            ORDER BY n DESC, role ASC
            """
        )
    ]

    by_found = [
        {"found_via": r["found_via"] or "(blank)", "n": r["n"]}
        for r in conn.execute(
            """
            SELECT COALESCE(NULLIF(TRIM(found_via), ''), '(blank)') AS found_via, COUNT(*) AS n
            FROM visitor_intros
            WHERE skipped = 0
            GROUP BY 1
            ORDER BY n DESC, found_via ASC
            """
        )
    ]

    recent = [
        {
            "ts": r["ts_utc"],
            "company": r["company"] or "",
            "role": r["role"] or "",
            "found_via": r["found_via"] or "",
            "kind": r["visitor_kind"] or "other",
            "skipped": bool(r["skipped"]),
        }
        for r in conn.execute(
            """
            SELECT ts_utc, company, role, found_via, visitor_kind, skipped
            FROM visitor_intros
            WHERE skipped = 0
            ORDER BY id DESC
            LIMIT 10
            """
        )
    ]

    return {
        "answered": answered,
        "skipped": skipped_n,
        "by_role": by_role,
        "by_found": by_found,
        "recent": recent,
    }
