# Manual steps (GitHub profile)

The `gh` token in this environment has `repo` / `gist` / `read:org` / `workflow` scopes, but not `user`. Updating the authenticated profile via `PATCH /user` returned 404 until the `user` scope is granted.

## Option A: refresh gh scope, then API

```bash
gh auth refresh -h github.com -s user
gh api -X PATCH /user \
  -f bio='Sr Staff Data Analyst at Achieve. Analytics platforms, metric contracts, and AI-assisted BI.' \
  -f company='Achieve' \
  -f blog='https://www.linkedin.com/in/oliveiralgm/' \
  -f email='oliveiralgm@gmail.com'
```

Confirm:

```bash
gh api user --jq '{bio,company,blog,email}'
```

## Option B: paste in the GitHub UI

1. Open https://github.com/settings/profile
2. **Bio** (under ~160 chars):

   `Sr Staff Data Analyst at Achieve. Analytics platforms, metric contracts, and AI-assisted BI.`

3. **Company**: `Achieve`
4. **Website**: `https://www.linkedin.com/in/oliveiralgm/`
5. **Public email** (if the dropdown allows): `oliveiralgm@gmail.com`
6. Save changes

## Current values observed before update

- bio: stale generic "8 years / data-driven insights" text
- company: empty
- blog: empty
- email: not returned by API (often private unless made public)
