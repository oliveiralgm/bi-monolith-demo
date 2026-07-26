# BI Monolith Demo

**Live playground:** [https://bi-monolith-demo.onrender.com/](https://bi-monolith-demo.onrender.com/)

> **Personal portfolio demo. Mock data and original code. Not the production systems or proprietary code from any employer.**

Public click-and-play demo (no access key). Free-tier Render may take ~30-60s on first hit after idle (cold start).

---

Public **Staff analytics platform** architecture demo for [Gustavo Oliveira](https://github.com/oliveiralgm). One Flask + Dash process auto-discovers dashboard modules, mounts metric-style mock surfaces, and includes a page-load telemetry stub plus AI-assisted analytics framing on the home page.

Built for reviewers evaluating Staff / Senior Analytics Engineer work: platform patterns (auto-mount, shared shell, adoption telemetry), experiment modernization (Tableau → Dash spirit), and lead conversion / consumer funnel readout.

Contact: [oliveiralgm@gmail.com](mailto:oliveiralgm@gmail.com) · [LinkedIn](https://www.linkedin.com/in/oliveiralgm/)

## Why this repo (for Staff AE / platform reviewers)

| Surface | What it demonstrates |
|---------|----------------------|
| **Lead Conversion** (`/d/lead-conversion/`) | Application → review → offer → funding with channel/cohort slices |
| **Pair Trader Lab** (`/d/pair-trader/`) | Spread / z-score pairs playground inspired by [pair_trader](https://github.com/oliveiralgm/pair_trader). Portfolio demo only. Not financial advice. |
| **Experiment Readout** | A/B sample size, lift, MoE, power-style hints (self-serve experiment owners) |
| **Platform Adoption** | DAU, peak users, per-dashboard usage + local sqlite page-load stub |
| **Stubs on home** | Metric contracts, AI-assisted analytics (full suite on request) |

Architecture signals: single process, `DASHBOARD` dict registration, key gate / public playground mode, deployable Blueprint.

## Live playground

**Live URL:** [https://bi-monolith-demo.onrender.com/](https://bi-monolith-demo.onrender.com/)

With `BI_DEMO_PUBLIC=1`, visitors open the samples with no key. Stub cards stay placeholders; email for the fuller suite walkthrough.

## What this repo includes

- Flask server hosting Dash apps in one process
- Auto-discovery: modules in `dashboards/` expose a `DASHBOARD` dict; `discovery.py` mounts each at `/d/<slug>/`
- Access key gate for local clones (`BI_DEMO_KEY` from env; no private key is committed)
- **Public playground mode** (`BI_DEMO_PUBLIC=1`): unlocks samples for click-and-play on hosted deploys
- Working samples: Lead Conversion (`/d/lead-conversion/`), Pair Trader Lab (`/d/pair-trader/`), Experiment Readout, Platform Adoption
- Alias redirects from older paths (`/d/intercom-funnel/`, `/d/consumer-funnel/`, `/d/lead-funnel/`)
- Pair Trader Lab uses Yahoo prices when available, otherwise a synthetic correlated series (offline-safe on Render)
- Home-page stubs for the fuller suite (contact for walkthrough)
- Telemetry stub writing page loads to local sqlite
- `Dockerfile`, `Procfile`, and `render.yaml` for free-tier hosting

## What stays private

Richer local modules and private walkthrough materials live outside this repo. Email or LinkedIn for a walkthrough of the complete set (metric contracts, AI-assisted surfaces, and related patterns).

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

Open `http://127.0.0.1:8050/`. Without the key you see the locked contact page. After unlock, the home page lists mounted samples plus stubs.

Unlock once via query param: `http://127.0.0.1:8050/?key=YOUR_KEY`

### Local public mode (optional)

```bash
# in .env
BI_DEMO_PUBLIC=1
```

Then `python app.py` opens the samples with no key prompt.

## Hosting notes

The public playground is already hosted at the Live playground URL above. This repo includes `render.yaml`, `Dockerfile`, and `Procfile` for that existing free-tier service. Free Render services sleep after idle time; the first request after sleep can take ~30-60s.

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

Authenticated HTML navigations append a row to `data/telemetry.sqlite`. Delete that file anytime to reset. The Platform Adoption sample charts mock suite DAU/peak plus this local stub.

## Request the full suite

Email [oliveiralgm@gmail.com](mailto:oliveiralgm@gmail.com) or message on [LinkedIn](https://www.linkedin.com/in/oliveiralgm/) for a walkthrough of the fuller set (metric contracts, AI-assisted analytics, and related platform patterns).
