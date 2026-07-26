# Manual steps

## 1) GitHub profile bio (API blocked here)

The `gh` token lacks the `user` scope, so `PATCH /user` returns 404. Paste in the UI, or refresh the scope.

### Paste at https://github.com/settings/profile

- **Bio** (~160 chars):

  `Sr Staff Data Analyst at Achieve. Analytics platforms, metric contracts, and AI-assisted BI.`

- **Company**: `Achieve`
- **Website**: `https://www.linkedin.com/in/oliveiralgm/`
- **Public email** (if available): `oliveiralgm@gmail.com`

### Or refresh gh scope

```bash
gh auth refresh -h github.com -s user
gh api -X PATCH /user \
  -f bio='Sr Staff Data Analyst at Achieve. Analytics platforms, metric contracts, and AI-assisted BI.' \
  -f company='Achieve' \
  -f blog='https://www.linkedin.com/in/oliveiralgm/' \
  -f email='oliveiralgm@gmail.com'
gh api user --jq '{bio,company,blog,email}'
```

Observed before update: stale generic bio, empty company/blog.

## 2) One-click hosted playground (Render)

No Render/Fly/Railway CLI login was available in this environment. Deploy files are already in the repo (`render.yaml`, `Dockerfile`, `Procfile`) with `BI_DEMO_PUBLIC=1`.

1. Open: https://render.com/deploy?repo=https://github.com/oliveiralgm/bi-monolith-demo
2. Sign in with GitHub.
3. Confirm the Blueprint (free web service). Env includes `BI_DEMO_PUBLIC=1`.
4. Wait for deploy. Open the `*.onrender.com` URL. Sample funnel should load with no key.
5. Optional: edit README "Live playground" and replace the placeholder with your URL.
6. Optional CLI later: `render login` then deploy from the Blueprint.

Free tier sleeps when idle; first hit after sleep can take ~30-60s.
