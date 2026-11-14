# 5. Publishing on GitHub Pages

GitHub Pages hosts the website for free at
**https://ali-fathi-st.github.io/waypoint/**. It only serves files. It can't run
a backend, which is why the site runs on sample data until the FastAPI server
is hosted somewhere else.

## How publishing works

```
you push to main ──► GitHub Actions runs .github/workflows/deploy-pages.yml
                        1. "Run tests"   npm test (stops here if anything fails)
                        2. "Deploy"      uploads frontend/ and publishes it
                     ──► site updated in about a minute
```

Only the `frontend/` folder is published. `docs/`, `tests/` and `backend/`
stay in the repository but never appear on the site.

## One-time setup

1. Open the repository on GitHub: https://github.com/ali-fathi-st/waypoint
2. Click **Settings** (top bar) → **Pages** (left menu).
3. Under **Build and deployment → Source**, choose **GitHub Actions**.
4. That's it. There's nothing else to configure.

## Publish (and re-publish)

Any push to `main` publishes. To publish without changing anything:

1. Go to the **Actions** tab.
2. Choose **Deploy site to GitHub Pages** on the left.
3. Click **Run workflow** → **Run workflow**.

Watch progress on the Actions tab. A green check means it's live. Click the
run, then the link under **deploy**, to open the site.

## Edit the site from your browser (no install)

1. Open a file on GitHub, e.g. `frontend/index.html`.
2. Click the pencil icon, make your change.
3. Click **Commit changes**. The site updates about a minute later.

## Edit on your computer

```bash
# make your changes, check them locally (see 01 Getting started), then:
npm test                          # optional: run the checks first
git add .
git commit -m "Describe what you changed"
git push
```

## Rules that keep the site working on Pages

The site lives at `/waypoint/`, not at the root of the domain. So:

- **Always use relative links:** `href="jobs.html"`, `src="js/pages/jobs.js"`.
  Never start a path with `/` (`/jobs.html` would point to
  `ali-fathi-st.github.io/jobs.html`, which doesn't exist).
- **File names are case-sensitive** on Pages: `Jobs.html` ≠ `jobs.html`. On
  Windows and Mac they look the same, so a wrong case works locally and breaks
  online. Keep everything lowercase.
- **No secrets.** Everything in `frontend/` is public. API keys belong in the
  backend's environment, never in `config.js`.

## Troubleshooting

| What you see | Why | Fix |
| --- | --- | --- |
| Red ✗ on "Run tests" | A test failed, so nothing was published | Open the run, read which test failed, fix it, push again |
| Red ✗ on "Deploy" with "Pages not enabled" or a 404 | Pages source isn't set | Do the one-time setup above |
| Site shows an old version | Browser cache | Hard refresh: `Ctrl + Shift + R` / `Cmd + Shift + R`. Wait a minute after the green check. |
| Page has no styles | A path starts with `/` or has the wrong case | Make it relative and lowercase |
| "Page not found" for a page that exists | Wrong case in the link, or the file isn't in `frontend/` | Check the exact file name |
| Blank page, no data | A JavaScript error | `F12` → Console shows the file and line |

## Custom domain (optional)

Settings → Pages → **Custom domain**. GitHub's guide:
https://docs.github.com/pages/configuring-a-custom-domain-for-your-github-pages-site

Next: [06 API contract](06-api-contract.md)
