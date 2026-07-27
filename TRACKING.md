# Tracking access to this demo

## What already exists

Page-load telemetry is built in:

1. `app.py` `gate_and_telemetry` records authenticated HTML GETs (home + `/d/<slug>/`).
2. Rows go to `data/telemetry.sqlite` via `telemetry.py` (path, slug, UA, visitor kind, client IP).
3. **Platform Adoption** (`/d/adoption/`) shows mock suite DAU/peak plus a live panel of those loads, split into **self** vs **other**.
4. Optional **visitor hello** popup (company / role / how found) posts to `/api/visitor-intro` and lands in the same sqlite. Aggregates show under Live telemetry. Skip or dismiss sets a 30-day `bi_demo_who` cookie so it does not nag.

It works the same on Render as locally, with one hard limit: Render free web services use **ephemeral disk**. Redeploys, sleeps, and instance recycles wipe `telemetry.sqlite`. Counts are "this instance session," not durable history.

## Mark yourself (self vs others)

Open once:

[https://bi-monolith-demo.onrender.com/?me=1](https://bi-monolith-demo.onrender.com/?me=1)

That sets a `bi_demo_me` cookie. Later hits from that browser are tagged `self`. Everyone else is `other`. Client IP is taken from `X-Forwarded-For` (or `request.remote_addr`) and stored only for visit classification on this demo.

On Platform Adoption you will see separate KPIs and charts for your visits vs other visitors, plus a light recent-hit line that can show IPs.

## Optional visitor hello

Friendly, dismissible popup on first visit (or until answer/skip). Answers are optional. Cookie `bi_demo_who` (30 days) stops the nag after Submit or Skip. To see it again: clear that cookie in the browser (Application → Cookies), or use a private window.

## How to view it

| Where | What you see |
| --- | --- |
| `/d/adoption/` | Mock suite DAU/peak; live **Your visits (self)** / **Other visitors** + charts + visitor hello counts (auto-refresh ~15s) |
| Locally | Inspect or delete `data/telemetry.sqlite` to reset |
| On Render | Same UI; do not expect persistence across deploys |

Suite DAU / peak / per-dashboard bars on that page are **mock data** from `data/mock.py`. Only the local page-load panel (and visitor hellos) are real hits from this deployment.

## Mock vs live (elsewhere)

Dashboard headers use badges:

- **Mock data** — Lead Conversion, Experiment Readout, and the suite charts on Platform Adoption
- **Live telemetry from this deployment** — Platform Adoption page-load panels and visitor hellos
- Pair Trader Lab — public Yahoo prices when reachable, otherwise synthetic fallback (KPI shows which)

## Privacy (short)

IPs are stored for visit classification on this demo only. Optional company/role/source answers are for the portfolio demo only and show on Platform Adoption (company only if submitted). Not used for advertising or shared with third parties. Wipe by deleting `telemetry.sqlite` (or redeploying on free Render).

## Render dashboard (built-in, free/Hobby)

In [Render Dashboard](https://dashboard.render.com) open the `bi-monolith-demo` web service:

1. **Metrics** → Network: total HTTP request volume (public traffic). Status filters help spot errors.
2. **Logs** → app stdout/stderr (Hobby: ~7 days). Useful for crashes and deploys, not a clean visitor funnel. Per-request HTTP access logs are a **Pro** feature.

Free/Hobby caveats: instances spin down after idle; cold starts look like gaps; request volume includes assets and Dash `_dash-*` traffic, so it is noisier than "unique visitors."

## Ranked options for a portfolio demo

1. **Render Metrics + Logs** — zero code. Good enough to prove the app gets traffic.
2. **Keep the sqlite stub as the demo feature** — best story for Staff analytics: Platform Adoption shows mock suite metrics + a live "this session" stub with self/other. Document the ephemeral limit in the subtitle (already does). Optional later: Turso / remote SQLite if you want durable real hits without changing the UI story.
3. **Structured logs you can grep** — `print`/`logging` one JSON line per page load; filter in Render Logs. Cheap, survives disk wipe, still short retention.
4. **GoatCounter / Umami / Plausible** — privacy-friendly unique visitors and paths. Best if you care about resume-link traffic over weeks. One script tag or middleware; separate from the adoption dashboard narrative.

Skip GA4 unless you already use it elsewhere; overkill for a gated portfolio demo.

## Practical recommendation

Use **Render Metrics** for "is anyone hitting this?" and keep **Platform Adoption** as the architecture demo (mock + live stub with self/other). Add GoatCounter only if you want durable, human-readable visitor counts without building storage.
