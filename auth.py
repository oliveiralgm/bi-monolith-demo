"""Lightweight access-key gate for the BI demo scaffold."""

from __future__ import annotations

import hmac
import os
from functools import wraps
from typing import Callable, Optional

from flask import Request, redirect, request, session, url_for


COOKIE_NAME = "bi_demo_auth"
SESSION_FLAG = "authenticated"


def public_demo_mode() -> bool:
    """Hosted playground: unlock the sample without a key when BI_DEMO_PUBLIC=1."""
    return (os.environ.get("BI_DEMO_PUBLIC") or "").strip() in {"1", "true", "True", "yes", "YES"}


def expected_key() -> str:
    return (os.environ.get("BI_DEMO_KEY") or "").strip()


def key_configured() -> bool:
    if public_demo_mode():
        return True
    return bool(expected_key())


def keys_match(candidate: Optional[str]) -> bool:
    expected = expected_key()
    if not expected or candidate is None:
        return False
    return hmac.compare_digest(candidate.strip(), expected)


def extract_key(req: Request) -> Optional[str]:
    """Accept key from query param, form body, Authorization Bearer, or cookie."""
    q = req.args.get("key")
    if q:
        return q
    if req.method == "POST":
        form_key = req.form.get("key")
        if form_key:
            return form_key
    auth = req.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    cookie = req.cookies.get(COOKIE_NAME)
    if cookie:
        return cookie
    return None


def is_authenticated(req: Request | None = None) -> bool:
    if public_demo_mode():
        return True
    req = req or request
    if session.get(SESSION_FLAG) is True:
        return True
    return keys_match(extract_key(req))


def mark_authenticated() -> None:
    session[SESSION_FLAG] = True
    session.permanent = True


def clear_authenticated() -> None:
    session.pop(SESSION_FLAG, None)


def require_access(view: Callable):
    """Flask view decorator: redirect to locked page when key is missing/invalid."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if is_authenticated():
            return view(*args, **kwargs)
        return redirect(url_for("locked", next=request.path))

    return wrapped
