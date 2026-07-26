"""
Public BI monolith scaffold for Gustavo Oliveira.

Single Flask process + auto-discovered Dash dashboards.
Portfolio architecture demo with mock data. Not Achieve production code.
"""

from __future__ import annotations

import os
import re
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, make_response, redirect, render_template_string, request, url_for

from auth import (
    COOKIE_NAME,
    clear_authenticated,
    expected_key,
    is_authenticated,
    key_configured,
    keys_match,
    mark_authenticated,
    public_demo_mode,
    require_access,
)
from discovery import discover_dashboards, mount_dashboards
from telemetry import record_page_load

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8050"))

server = Flask(__name__, static_folder="assets", static_url_path="/assets")
server.secret_key = os.environ.get("FLASK_SECRET_KEY") or "dev-only-change-me"
server.permanent_session_lifetime = timedelta(days=7)

DASHBOARDS = discover_dashboards()
DASH_APPS = mount_dashboards(server, DASHBOARDS)
_SLUG_RE = re.compile(r"^/d/([^/]+)")

# Additional portfolio topics shown as stubs on the home page.
# Full implementations stay in the private local demo; request access for a walkthrough.
STUB_DASHBOARDS = [
    {
        "title": "HOVER Jobs Forecast",
        "summary": "Weekly job volume, roof/complete mix, and weather weeks. Full module available on request.",
        "source_topic": "GitHub: HOVER_jobs_forecast",
    },
    {
        "title": "Experiment Readout",
        "summary": "A/B readout with sample size and power-style hints. Full module available on request.",
        "source_topic": "Tableau to Dash spirit",
    },
    {
        "title": "Adoption Telemetry",
        "summary": "Page-load adoption stub reading local sqlite telemetry. Full module available on request.",
        "source_topic": "Platform adoption",
    },
]


LOCKED_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Access required · BI Demo</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,560&family=IBM+Plex+Sans:wght@400;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="/assets/style.css" />
</head>
<body>
  <main class="shell locked">
    <div class="brand">Gustavo Oliveira · BI platform demo</div>
    <h1>Contact Gustavo Oliveira for an access key</h1>
    <p class="lede">
      This public scaffold shows the mounting pattern from his resume: one Flask/Dash app,
      dashboards that register themselves, and a page-load telemetry stub. Enter a local
      key from your <code>.env</code> to unlock the sample dashboard.
    </p>
    <div class="panel">
      <form method="post" action="{{ url_for('login') }}">
        <input type="hidden" name="next" value="{{ next_url }}" />
        <label for="key">Access key</label>
        <input id="key" name="key" type="password" autocomplete="current-password" required />
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <button class="btn" type="submit">Unlock demo</button>
      </form>
      <div class="contact">
        <div><a href="mailto:oliveiralgm@gmail.com">oliveiralgm@gmail.com</a></div>
        <div><a href="https://www.linkedin.com/in/oliveiralgm/" target="_blank" rel="noopener">LinkedIn</a></div>
      </div>
    </div>
    <p class="footnote">Mock data only. Not Achieve production code.</p>
  </main>
</body>
</html>
"""


HOME_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BI Monolith Demo · Gustavo Oliveira</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,560&family=IBM+Plex+Sans:wght@400;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="/assets/style.css" />
</head>
<body>
  <main class="shell">
    <div class="topbar">
      <div class="brand">Gustavo Oliveira · BI platform demo</div>
      {% if public_mode %}
      <span class="badge">Public playground</span>
      {% else %}
      <a href="{{ url_for('logout') }}">Lock again</a>
      {% endif %}
    </div>
    <h1>Auto-discovered dashboards</h1>
    <p class="lede">
      One Flask process mounts every module in <code>dashboards/</code> that exposes a
      <code>DASHBOARD</code> dict. Add a file, restart, it shows up here. This public repo
      ships one working sample; other portfolio topics are listed as stubs
      {% if public_mode %}(full implementations available on request){% endif %}.
    </p>
    <div class="card-list">
      {% for d in dashboards %}
      <a class="dash-card" href="/d/{{ d.slug }}/">
        <h2>{{ d.title }}</h2>
        <p>{{ d.summary }}</p>
        <div class="meta">{{ d.source_topic }} · live sample</div>
      </a>
      {% endfor %}
      {% for s in stubs %}
      <div class="dash-card stub-card">
        <h2>{{ s.title }}</h2>
        <p>{{ s.summary }}</p>
        <div class="meta">{{ s.source_topic }} · full implementation on request</div>
      </div>
      {% endfor %}
    </div>
    <p class="footnote">
      {{ dashboards|length }} dashboard{{ '' if dashboards|length == 1 else 's' }} mounted ·
      mock data · telemetry stub writing to <code>data/telemetry.sqlite</code> ·
      contact <a href="mailto:oliveiralgm@gmail.com">oliveiralgm@gmail.com</a> for the full set
    </p>
  </main>
</body>
</html>
"""


@server.before_request
def gate_and_telemetry():
    path = request.path or "/"

    if path.startswith("/assets") or path in {"/locked", "/login", "/healthz"}:
        return None

    if not key_configured():
        return render_template_string(
            LOCKED_HTML,
            next_url="/",
            error="BI_DEMO_KEY is not set. Copy .env.example to .env and set a key.",
        ), 503

    qkey = request.args.get("key")
    if qkey and keys_match(qkey):
        mark_authenticated()

    authenticated = is_authenticated()

    if "/_dash" in path or path.endswith((".js", ".css", ".map", ".ico")):
        if authenticated:
            return None
        return redirect(url_for("locked", next="/"))

    if not authenticated:
        nxt = path if path.startswith("/") else "/"
        return redirect(url_for("locked", next=nxt))

    if request.method == "GET" and "/_dash" not in path and not path.startswith("/assets"):
        m = _SLUG_RE.match(path)
        slug = m.group(1) if m else ("home" if path == "/" else None)
        record_page_load(path, dashboard_slug=slug, user_agent=request.headers.get("User-Agent"))

    return None


@server.get("/healthz")
def healthz():
    return {"ok": True, "dashboards": [d.slug for d in DASHBOARDS]}


@server.route("/locked", methods=["GET"])
def locked():
    if is_authenticated():
        return redirect(request.args.get("next") or "/")
    return render_template_string(
        LOCKED_HTML,
        next_url=request.args.get("next") or "/",
        error=None,
    )


@server.route("/login", methods=["POST"])
def login():
    candidate = request.form.get("key", "")
    next_url = request.form.get("next") or "/"
    if not keys_match(candidate):
        return render_template_string(
            LOCKED_HTML,
            next_url=next_url,
            error="That key is not valid. Contact Gustavo for access.",
        ), 401

    mark_authenticated()
    resp = make_response(redirect(next_url))
    resp.set_cookie(
        COOKIE_NAME,
        expected_key(),
        httponly=True,
        samesite="Lax",
        max_age=7 * 24 * 3600,
    )
    return resp


@server.get("/logout")
def logout():
    clear_authenticated()
    resp = make_response(redirect(url_for("locked")))
    resp.delete_cookie(COOKIE_NAME)
    return resp


@server.get("/")
@require_access
def home():
    return render_template_string(
        HOME_HTML,
        dashboards=DASHBOARDS,
        stubs=STUB_DASHBOARDS,
        public_mode=public_demo_mode(),
    )


def main():
    if not key_configured():
        print("WARNING: BI_DEMO_KEY is empty. Copy .env.example to .env first.")
    mode = "public playground (BI_DEMO_PUBLIC=1)" if public_demo_mode() else "key gate"
    print(f"Mounted {len(DASHBOARDS)} dashboard(s): {[d.slug for d in DASHBOARDS]}")
    print(f"Auth mode: {mode}")
    print(f"Open http://{HOST}:{PORT}/")
    server.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    main()
