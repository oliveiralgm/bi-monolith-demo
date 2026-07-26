# BI Monolith Demo (public scaffold)

Public architecture demo for **Gustavo Oliveira**. One Flask + Dash process auto-discovers dashboard modules, mounts them under a single app, and includes a tiny page-load telemetry stub.

This is a **personal portfolio scaffold**, not Achieve production code. Data is synthetic. Full dashboard implementations beyond the sample are available on request.

Contact: [oliveiralgm@gmail.com](mailto:oliveiralgm@gmail.com) · [LinkedIn](https://www.linkedin.com/in/oliveiralgm/)

## Live playground

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/oliveiralgm/bi-monolith-demo)

**Hosted demo:** set after first deploy (see Deploy below). With `BI_DEMO_PUBLIC=1`, visitors open the sample with no key. Stub cards stay placeholders; the fuller suite needs a walkthrough.

If a live URL is already running, it will be linked here after deploy:

- Live URL: _(add after Render finishes, e.g. `https://bi-monolith-demo.onrender.com`)_

## What this repo includes

- Flask server hosting Dash apps in one process
- Auto-discovery: modules in `dashboards/` expose a `DASHBOARD` dict; `discovery.py` mounts each at `/d/<slug>/`
- Access key gate for local clones (`BI_DEMO_KEY` from env; no real private key is committed)
- **Public playground mode** (`BI_DEMO_PUBLIC=1`): unlocks the sample for click-and-play on hosted deploys
- Locked contact page when public mode is off and no valid key is present
- **One working sample**: Lead Funnel Conversion (`/d/intercom-funnel/`) with mock data
- Home-page stub cards for other portfolio topics (full modules on request)
- Telemetry stub that writes page loads to local sqlite
- `Dockerfile`, `Procfile`, and `render.yaml` for free-tier hosting

## What stays private

The fuller local demo (additional dashboards, private walkthrough materials) lives outside this repo. Email or LinkedIn for a walkthrough of the complete set.

## Run locally (key gate)

```bash
git clone https://github.com/oliveiralgm/bi-monolith-demo.git
cd bi-monolith-demo
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: set BI_DEMO_KEY, keep BI_DEMO_PUBLIC=0
python app.py
```

Open `http://127.0.0.1:8050/`. Without the key you see the locked contact page. After unlock, the home page lists the mounted sample plus stubs.

Unlock once via query param: `http://127.0.0.1:8050/?key=YOUR_KEY`

### Local public mode (optional)

To mimic the hosted playground locally:

```bash
# in .env
BI_DEMO_PUBLIC=1
```

Then `python app.py` opens the sample with no key prompt.

## Deploy (Render free tier)

1. Push this repo to GitHub (already the intended source).
2. Click **Deploy to Render** above, or open:
   `https://render.com/deploy?repo=https://github.com/oliveiralgm/bi-monolith-demo`
3. Sign in to Render (GitHub OAuth is fine).
4. Confirm the Blueprint: `BI_DEMO_PUBLIC=1` is set so visitors can play without a key.
5. After deploy, open the `*.onrender.com` URL and try **Lead Funnel Conversion**.
6. Paste that URL into the Live playground section of this README (or pin it from your profile).

Free Render services sleep after idle time; the first request after sleep can take ~30-60s.

Docker alternative:

```bash
docker build -t bi-monolith-demo .
docker run --rm -p 8050:8050 -e BI_DEMO_PUBLIC=1 bi-monolith-demo
```

## Access key (local / private walkthrough)

1. Set `BI_DEMO_KEY` in `.env` (never commit `.env`).
2. Use any string you pick for local runs; share a private key only for a hosted walkthrough of extra material.
3. Comparison uses `hmac.compare_digest`. This is a demo gate, not enterprise auth.
4. Hosted public playground should use `BI_DEMO_PUBLIC=1` instead of publishing a private key.

## How auto-mount works

1. Create `dashboards/my_thing.py`.
2. Expose:

```python
DASHBOARD = {
    "slug": "my-thing",
    "title": "My Thing",
    "summary": "One line for the home page.",
    "source_topic": "Where the idea came from",
    "order": 50,
    "layout": layout,
    "register_callbacks": register_callbacks,  # optional
}
```

3. Restart `python app.py`. It appears on the home page and at `/d/my-thing/`.

Modules whose names start with `_` are skipped (shared helpers).

## Telemetry stub

Authenticated HTML navigations append a row to `data/telemetry.sqlite`. Delete that file anytime to reset. The public scaffold does not ship the adoption dashboard that charts those rows.

## Request the full dashboards

Email [oliveiralgm@gmail.com](mailto:oliveiralgm@gmail.com) or message on [LinkedIn](https://www.linkedin.com/in/oliveiralgm/) for a walkthrough of the fuller set (forecast, experiment readout, adoption, and related patterns such as metric contracts).
