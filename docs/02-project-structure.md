# 2. Project structure

Every file, and what it's for. The rule of thumb: **HTML is structure, CSS is
looks, JavaScript is behaviour and data.** They never mix (two small,
documented exceptions are noted below).

```
waypoint/
├── README.md                  Start here
├── package.json               Only for running tests (no dependencies)
├── .gitignore                 Files git should never commit
├── .github/workflows/
│   └── deploy-pages.yml       Publishes frontend/ to GitHub Pages on every push
├── docs/                      These guides
├── tests/                     Automated checks (npm test)
├── backend/                   The future FastAPI server (plan only, for now)
└── frontend/                  The website. This is all GitHub Pages publishes.
```

## frontend/: the website

### Pages (one HTML file each)

| File | Address | What it shows |
| --- | --- | --- |
| `index.html` | `/` | Dashboard: summary numbers, jobs worth reviewing, chart, recent activity |
| `jobs.html` | `/jobs.html?q=analyst&min=70` | All jobs, with search and filters |
| `job.html` | `/job.html?id=job_001` | One job: description, match breakdown, skills |
| `applications.html` | `/applications.html?view=table` | All applications, as a board or a table |
| `application.html` | `/application.html?id=app_001` | One application: timeline, notes, materials, follow-up, interviews |
| `documents.html` | `/documents.html` | Résumé versions and cover-letter drafts |
| `profile.html` | `/profile.html` | Your skills, experience and preferences |
| `settings.html` | `/settings.html?tab=account` | Sources, notifications, account, developer tools |
| `404.html` | any wrong address | "Page not found" (GitHub Pages uses it automatically) |

Each page's HTML holds the fixed structure: headings, panels, forms and
dialogs. Its JavaScript fills in the data. Repeated pieces (a skill row, a
job source panel) are written once as a `<template>` in the HTML and copied
by the script.

### css/: styles, loaded in this order

| File | Contents |
| --- | --- |
| `tokens.css` | **The design system's values**: every color, font size, spacing step and corner radius, as CSS variables. Change the look here. |
| `base.css` | Resets and bare-element defaults (body text, links, focus outline). No classes. |
| `layout.css` | The page frame: sidebar, mobile top bar and menu, page header, grids. |
| `components.css` | Reusable pieces: buttons, inputs, badges, panels, tables, tabs, dialogs, toasts, loading/empty/error states. |
| `pages.css` | Pieces used by one page or feature: dashboard stats, chart, match breakdown, board, timeline, profile rows, settings. |

### js/: behaviour

```
js/
├── config.js          THE settings file: sample data or your backend
├── api/               Everything about getting data
│   ├── api.js         The one door all pages use; picks mock or http
│   ├── mock-api.js    Fake backend using sample data (default)
│   ├── http-api.js    Real backend calls (FastAPI)
│   ├── contract.js    Fields each record must have (checks backend replies)
│   └── errors.js      One error type for every failure + friendly messages
├── data/
│   └── sample-data.js Fictional jobs, applications, profile + the match-score rules
├── lib/               Small helpers with no knowledge of pages
│   ├── dom.js         h() to build elements safely, $() to find them
│   ├── format.js      Dates, money, percentages
│   ├── status.js      Status names and which status changes are allowed
│   └── url.js         Read and write ?query=params
├── ui/                Pieces of interface used by several pages
│   ├── shell.js       Sidebar + mobile menu, built on every page
│   ├── icons.js       Inline SVG icons (Lucide, ISC license)
│   ├── toast.js       Short confirmations ("Notes saved")
│   ├── dialog.js      Dialog helpers + "Are you sure?" confirmations
│   ├── states.js      Loading, empty and error states
│   ├── badges.js      Status badges (icon + word)
│   ├── match.js       Match score bar and the full score breakdown
│   ├── chart.js       The SVG bar chart on the dashboard
│   ├── job-actions.js Shortlist / Dismiss / Restore buttons
│   ├── status-select.js The "Move to..." dropdown for applications
│   ├── follow-up.js   "Follow up Nov 24" / "overdue" labels
│   ├── tag-input.js   Chips input (titles, locations, keywords)
│   └── save-file.js   Download the data export
└── pages/             One script per HTML page (same name)
    ├── dashboard.js   for index.html
    ├── jobs.js, job.js, applications.js, application.js,
    └── documents.js, profile.js, settings.js
```

**Where to look first:**

- To change what a page shows: `frontend/<page>.html`, then `js/pages/<page>.js`.
- To change colors or spacing: `css/tokens.css`.
- To connect the backend: `js/config.js` (see [07](07-connecting-the-backend.md)).
- To change the sample data: `js/data/sample-data.js`.

### assets/

| File | What |
| --- | --- |
| `logo.svg` | The Waypoint mark (also the browser-tab icon) |
| `fonts/Geist-Variable.woff2` | The Geist typeface, served locally so nothing loads from other sites |
| `fonts/Geist-LICENSE.txt` | Its license (SIL Open Font License) |

### The two exceptions to "never mix"

1. **`404.html` has its styles inline.** GitHub Pages shows it for wrong
   addresses at any depth (`/waypoint/a/b/c`), where relative links to `css/`
   would break.
2. **Bar widths are set inline from JavaScript** (`style="width: 72%"`) for
   the match-score bars, because the width *is* the data.

## tests/

Automated checks using Node's built-in test runner. See [08 Testing](08-testing.md).

## backend/

Empty for now except its README, which lays out the FastAPI plan. The frontend
is designed so the backend can be added one endpoint at a time.

Next: [03 How the frontend works](03-how-the-frontend-works.md)
