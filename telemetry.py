"""Tiny page-load telemetry stub (local sqlite). Not a warehouse pipeline."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

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

_PAGE_LOAD_EXTRA_COLS = (
    ("referrer", "TEXT"),
    ("referrer_host", "TEXT"),
    ("source_class", "TEXT"),
    ("utm_source", "TEXT"),
    ("utm_medium", "TEXT"),
    ("utm_campaign", "TEXT"),
    ("ref_param", "TEXT"),
)


def referrer_host(referrer: str | None) -> str:
    """Hostname from a Referer URL, or empty."""
    raw = (referrer or "").strip()
    if not raw:
        return ""
    try:
        host = (urlparse(raw).hostname or "").lower().strip(".")
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host[:120]


def _classify_hint(hint: str) -> str:
    h = hint.strip().lower()
    if not h:
        return "Direct"
    if "github" in h:
        return "GitHub"
    if "linkedin" in h:
        return "LinkedIn"
    if "google" in h:
        return "Google"
    if h in {"direct", "none", "(direct)", "render", "onrender"}:
        return "Direct"
    if h in {"resume", "cv"}:
        return "Resume"
    # Keep a short custom label (e.g. utm_source=newsletter).
    cleaned = hint.strip()[:64]
    return cleaned or "Other"


def classify_source(
    referrer: str | None = None,
    utm_source: str | None = None,
    ref: str | None = None,
) -> str:
    """Light traffic class from UTM/ref first, else Referer host."""
    hint = (utm_source or "").strip() or (ref or "").strip()
    if hint:
        return _classify_hint(hint)

    host = referrer_host(referrer)
    if not host:
        return "Direct"
    if "github.com" in host or host.endswith("github.io"):
        return "GitHub"
    if "linkedin." in host or host == "linkedin.com":
        return "LinkedIn"
    if host == "google.com" or host.endswith(".google.com") or host.startswith("google."):
        return "Google"
    if "onrender.com" in host or host.endswith("render.com"):
        return "Direct"
    if host in {"localhost", "127.0.0.1"}:
        return "Direct"
    return host or "Other"


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
            client_ip TEXT,
            referrer TEXT,
            referrer_host TEXT,
            source_class TEXT,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            ref_param TEXT
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
    for name, decl in _PAGE_LOAD_EXTRA_COLS:
        if name not in cols:
            conn.execute(f"ALTER TABLE page_loads ADD COLUMN {name} {decl}")
    conn.commit()
    return conn


def record_page_load(
    path: str,
    dashboard_slug: str | None = None,
    user_agent: str | None = None,
    visitor_kind: str | None = None,
    client_ip: str | None = None,
    referrer: str | None = None,
    referrer_host_value: str | None = None,
    source_class: str | None = None,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    ref_param: str | None = None,
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    kind = (visitor_kind or "other").strip().lower()
    if kind not in {"self", "other"}:
        kind = "other"
    ref_raw = (referrer or "")[:500]
    host = (referrer_host_value or referrer_host(ref_raw) or "")[:120]
    src = (source_class or classify_source(ref_raw, utm_source, ref_param) or "Direct")[:64]
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO page_loads
                    (ts_utc, path, dashboard_slug, user_agent, visitor_kind, client_ip,
                     referrer, referrer_host, source_class,
                     utm_source, utm_medium, utm_campaign, ref_param)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    path,
                    dashboard_slug,
                    (user_agent or "")[:240],
                    kind,
                    (client_ip or "")[:64],
                    ref_raw,
                    host,
                    src,
                    (utm_source or "")[:64],
                    (utm_medium or "")[:64],
                    (utm_campaign or "")[:64],
                    (ref_param or "")[:64],
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


def _by_source(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT COALESCE(NULLIF(TRIM(source_class), ''), 'Direct') AS source_class, COUNT(*) AS n
        FROM page_loads
        GROUP BY 1
        ORDER BY n DESC, source_class ASC
        """
    )
    return [{"source": r["source_class"], "loads": r["n"]} for r in rows]


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
                    "source": r["source_class"] or "Direct",
                    "referrer_host": r["referrer_host"] or "",
                    "utm_source": r["utm_source"] or "",
                }
                for r in conn.execute(
                    """
                    SELECT ts_utc, path, visitor_kind, client_ip,
                           source_class, referrer_host, utm_source
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
                "by_source": _by_source(conn),
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
