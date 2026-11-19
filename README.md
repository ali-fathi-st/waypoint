# Waypoint

A job search tracker. It collects job postings, ranks them against your
profile and explains every score, then tracks each application from
"saved" to "offer", with follow-up reminders.

**Live demo:** https://ali-fathi-st.github.io/waypoint/ (runs on fictional
sample data; nothing you click there is real or sent anywhere)

| Part | Folder | Status |
| --- | --- | --- |
| Website (what you see) | [`frontend/`](frontend/) | Done. Plain HTML, CSS and JavaScript. Runs on sample data. |
| Server and database | [`backend/`](backend/) | Python + FastAPI + PostgreSQL. Runs on your computer. |
| Guides | [`docs/`](docs/) | How everything works and how to change it. |
| Tests | [`tests/`](tests/) | Checks the rules (dates, statuses, API). |

## What you can do in it

- **Dashboard**: where your search stands, new jobs worth a look, follow-ups due.
- **Jobs**: search and filter postings; shortlist or dismiss them.
- **Job page**: the full posting, plus a breakdown showing exactly how its match score adds up.
- **Applications**: a board or table of everything you're pursuing.
- **Application page**: timeline, notes, the résumé and cover letter you used, follow-up date, interviews.
- **Documents**: résumé versions and cover-letter drafts.
- **Profile**: your skills, experience and what you're looking for.
- **Settings**: job sources, notifications, export or delete your data.

Two rules are built into the design:

1. **Waypoint never applies for you.** You apply on the employer's site, then
   click "Record as applied" and confirm you did it.
2. **Nothing is invented.** Scores come from your profile, and the sample data
   is clearly labelled as fictional.

## Run it on your computer (2 minutes)

You need [Python](https://www.python.org/downloads/) (already on most Macs and
Linux) or [Node.js](https://nodejs.org/).

```bash
git clone https://github.com/ali-fathi-st/waypoint.git
cd waypoint
python3 -m http.server 8080 --directory frontend
```

Open **http://localhost:8080**. Full instructions, including Windows and
VS Code, are in [docs/01-getting-started.md](docs/01-getting-started.md).

> Double-clicking `index.html` won't work: browsers block JavaScript modules
> opened as files. Use a local server, as above.

## Put it on the internet

Every push to `main` publishes `frontend/` to GitHub Pages automatically.
One-time setup: **Settings → Pages → Source: GitHub Actions**.
Step by step: [docs/05-github-pages.md](docs/05-github-pages.md).

## Documentation

| Guide | Read it when you want to... |
| --- | --- |
| [01 Getting started](docs/01-getting-started.md) | run the site on your computer |
| [02 Project structure](docs/02-project-structure.md) | know what every file is for |
| [03 How the frontend works](docs/03-how-the-frontend-works.md) | understand the code, or add a page |
| [04 Design system](docs/04-design-system.md) | change colors and styles, or reuse components |
| [05 GitHub Pages](docs/05-github-pages.md) | publish the site, or fix a deployment |
| [06 API contract](docs/06-api-contract.md) | build the backend endpoints |
| [07 Connecting the backend](docs/07-connecting-the-backend.md) | switch from sample data to your FastAPI server |
| [08 Testing](docs/08-testing.md) | check that nothing broke |
| [09 The backend](docs/09-backend.md) | run it, collect real jobs, use the API from your own automations |

## How it's built

- **No build step, no dependencies.** Every file in `frontend/` is served
  exactly as written. Change a file, refresh the browser.
- **HTML, CSS and JavaScript are kept separate.** Each page has its own
  `.html` file and its own script in `js/pages/`. Styles live in `css/`.
- **One switch for the backend.** `frontend/js/config.js` decides whether data
  comes from the built-in sample data or from the FastAPI server, and can
  connect one endpoint at a time.

## Roadmap

1. ~~Frontend with sample data~~ ✓
2. ~~Publish on GitHub Pages~~ ✓
3. ~~Backend: FastAPI + PostgreSQL, every endpoint~~ ✓ ([docs/09](docs/09-backend.md))
4. ~~Job collection from Greenhouse, Lever and Adzuna~~ ✓ (scheduled on your computer)
5. Better matching (skills extraction, text similarity) and AI-drafted cover letters you review before use
6. Sign-in
