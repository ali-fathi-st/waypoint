# Frontend

The Waypoint website: plain HTML, CSS and JavaScript, with no build step and
no dependencies. This folder is exactly what GitHub Pages publishes.

```
*.html        one file per page (index.html is the dashboard)
css/          tokens → base → layout → components → pages
js/config.js  sample data or your backend: the only setting to change
js/api/       getting data (mock or FastAPI)
js/pages/     one script per page, same name as its HTML file
js/ui/        pieces shared by pages (menu, dialogs, badges, ...)
js/lib/       small helpers (dates, statuses, building elements)
js/data/      the fictional sample data
assets/       logo and font
```

Run it: `python3 -m http.server 8080 --directory frontend` from the repository
root, then open http://localhost:8080.

Everything else is in [`../docs/`](../docs/README.md). Start with
[02 Project structure](../docs/02-project-structure.md) and
[03 How the frontend works](../docs/03-how-the-frontend-works.md).
