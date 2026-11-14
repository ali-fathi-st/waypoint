# Waypoint documentation

Read them in order the first time; after that, jump to what you need.

| # | Guide | What's in it |
| --- | --- | --- |
| 01 | [Getting started](01-getting-started.md) | Run the site on your computer; a quick tour; fixes for common problems |
| 02 | [Project structure](02-project-structure.md) | Every folder and file, and where to look first |
| 03 | [How the frontend works](03-how-the-frontend-works.md) | Page lifecycle, the API layer, safe HTML, status rules, match scoring, adding a page |
| 04 | [Design system](04-design-system.md) | Colors, type, spacing, component snippets, writing style |
| 05 | [GitHub Pages](05-github-pages.md) | Publishing, editing online, rules for Pages, troubleshooting |
| 06 | [API contract](06-api-contract.md) | Every endpoint, field and rule for the FastAPI backend, with example JSON |
| 07 | [Connecting the backend](07-connecting-the-backend.md) | Switching from sample data, one endpoint at a time |
| 08 | [Testing](08-testing.md) | Automated tests and a click-through checklist |

Also: [backend/README.md](../backend/README.md), the plan for the server.

## Words used in these guides

| Word | Meaning here |
| --- | --- |
| **Frontend** | The website: what runs in the browser (`frontend/`) |
| **Backend** | The server that stores data and collects jobs (`backend/`, FastAPI) |
| **API** | The set of addresses the frontend calls to get or change data, e.g. `GET /api/v1/jobs` |
| **Mock / sample data** | Fictional data built into the frontend, so it works without a backend |
| **Endpoint / operation** | One API action, e.g. "list jobs" |
| **Module** | A JavaScript file that shares functions with `export` and uses others with `import` |
| **localStorage** | A small storage area in your browser, per website |
| **CORS** | The browser rule that a server must allow a website before the site can call it |
| **Deploy / publish** | Put the current version online |
