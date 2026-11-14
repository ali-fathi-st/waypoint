# 3. How the frontend works

This guide follows one page from the moment it loads, then shows how to add
your own page.

## What happens when a page loads

Take `jobs.html`:

```
1. Browser loads jobs.html          the structure: header, filter form, empty results area
2. Browser loads the 5 CSS files    the look
3. Browser runs js/pages/jobs.js    the behaviour (type="module", so it runs after the HTML is ready)
       │
       ├─ initShell()               builds the sidebar and mobile menu into <div id="shell">
       ├─ reads ?q=...&min=...      puts saved filters back into the form
       └─ load()
            ├─ shows grey placeholder rows
            ├─ await api.listJobs({...})     asks for data (sample data or backend)
            └─ renders the table, or an empty or error message
```

Every page script follows the same shape:

```js
import { initShell } from "../ui/shell.js";
import { api } from "../api/api.js";

initShell(); // 1. navigation

function renderSomething(data) { ... } // 2. turn data into elements

async function load() { // 3. fetch, then render
  try {
    renderSomething(await api.getSomething());
  } catch (error) {
    render($("#error"), errorState(error, load)); // shows "Try again"
  }
}

load();
```

## Getting data: one door, two rooms

Pages never fetch anything directly. They call `api` from `js/api/api.js`:

```
 page script ──► api.listJobs()
                     │
     js/config.js says apiMode: "mock" ──► mock-api.js  (sample data, in your browser)
                       apiMode: "http" ──► http-api.js  (your FastAPI server)
                       apiMode: "hybrid" ─► some of each
```

Both implementations have **the same functions** and return **the same
shapes**, so a page can't tell which one answered. That's what makes swapping
in the backend a one-line change.

Every function returns a Promise, so pages always use `await`, even with
sample data. The mock adds a short delay on purpose, so loading states are
real.

### The operations

| Area | Functions |
| --- | --- |
| Jobs | `listJobs(filters)`, `getJob(id)`, `updateJobStatus(id, status)` |
| Applications | `listApplications()`, `getApplication(id)`, `createApplication({job_id})`, `updateApplication(id, changes)`, `confirmSubmission(id, details)`, `addInterview(id, details)` |
| Dashboard | `getDashboardMetrics()` |
| Profile | `getCandidateProfile()`, `updateCandidateProfile(profile)` |
| Documents | `listDocuments(filters)`, `uploadDocument(details)`, `updateDocument(id, changes)` |
| Settings | `getSettings()`, `updateSettings(changes)`, `exportData()`, `deleteAllData()` |

The exact data each one sends and receives is in [06 API contract](06-api-contract.md).

## Building HTML safely with h()

All dynamic HTML is made with `h()` from `js/lib/dom.js`:

```js
h("a", { href: "job.html?id=job_001", class: "title-link" }, job.title)
// <a href="job.html?id=job_001" class="title-link">Data Engineer</a>

h("button", { type: "button", class: "btn", onclick: save }, icon("check"), "Save")
```

**Text passed to `h()` is always inserted as text, never as HTML.** That
matters because job descriptions come from other websites. If a posting
contained `<script>`, it would show up as harmless text instead of running.
So: never use `innerHTML` with data. (`icons.js` uses it only for its own
fixed icon drawings.)

Other helpers in `dom.js`:

| Helper | Does |
| --- | --- |
| `$("#id")` | Find one element; throws a clear error if it's missing |
| `$$(".class")` | Find all, as an array |
| `render(el, ...children)` | Replace everything inside `el` |
| `debounce(fn, 300)` | Wait until typing pauses (used by search boxes) |
| `withBusy(button, "Saving...", fn)` | Disable a button and change its text while `fn` runs |

## The application rules

`js/lib/status.js` holds the status rules. The UI only offers moves that are
allowed:

```
saved ─► preparing ─► ready_for_review ─┐
  │          │              │           │  "Record as applied" (confirmation dialog)
  └──────────┴──────────────┴───────────┴─► applied ─► interview ─► offer
                                             any open status ─► rejected / withdrawn (closed)
```

- **"Applied" is never a direct option.** It's only reachable through the
  "Record as applied" dialog, where you confirm you submitted it yourself.
- A follow-up reminder exists only while an application is *applied* or
  *interviewing*. Closing it clears the reminder.

The mock API enforces the same rules, and the backend must too (see
[06](06-api-contract.md)).

## State that lives in the address bar

Filters and tabs are kept in the URL's query string (`?q=analyst&min=70`).
That gives you three things for free: refresh keeps your filters, you can
bookmark a view, and links can open a specific state, e.g.
`application.html?id=app_002&confirm=1` opens the "Record as applied" dialog.

Helpers: `getParam`, `getParams`, `setParams` in `js/lib/url.js`.

## State saved in your browser

| Key (localStorage) | What |
| --- | --- |
| `waypoint.mock-db.v1` | The sample data, including your changes |
| `waypoint.mock-scenario` | Normal / empty / slow / error (Settings → Developer) |
| `waypoint.howto-hidden` | You hid the "How Waypoint works" guide |

Nothing else is stored, and nothing leaves your browser in mock mode.

## How the match score works

`scoreJob()` in `js/data/sample-data.js`. Each factor scores 0 to 1 and is
multiplied by a fixed weight. The weights add up to 1, so the total is out
of 100:

| Factor | Weight | Scores 1 when... |
| --- | --- | --- |
| Required skills | 40% | you have all of them (partial credit per skill) |
| Nice-to-have skills | 15% | you have all of them |
| Title | 20% | the title contains one of your target titles (0.5 if related, 0 if excluded) |
| Location | 10% | it's remote or in one of your cities |
| Work arrangement | 10% | it's one you accept (0.5 if not stated) |
| Salary | 5% | the top of the range reaches your minimum (0.5 if not posted) |

The job page shows every factor with its points, so the score is never a
mystery. When the backend exists, this logic moves there (Python) and the
frontend just displays what it receives.

## Add a new page in 5 steps

Example: a "Companies" page.

1. **Copy an HTML page.** Duplicate `documents.html` as `companies.html`.
   Change `<title>`, `<body data-page="companies">`, the `<h1>`, and the
   script at the bottom to `js/pages/companies.js`. Replace the content
   inside `<main>` with what you need, e.g. `<section class="panel" id="list"></section>`.
2. **Add it to the menu.** In `js/ui/shell.js`, add to `NAV_ITEMS`:
   `{ page: "companies", href: "companies.html", label: "Companies", icon: "jobs" }`.
3. **Write the script** `js/pages/companies.js`:
   ```js
   import { initShell } from "../ui/shell.js";
   import { api } from "../api/api.js";
   import { h, render, $ } from "../lib/dom.js";
   import { errorState, loadingRows } from "../ui/states.js";

   initShell();

   async function load() {
     render($("#list"), loadingRows(4));
     try {
       const { items } = await api.listJobs({ review_status: "all", limit: 100 });
       const names = [...new Set(items.map((j) => j.company.name))].sort();
       render($("#list"), h("ul", { class: "list" }, names.map((n) => h("li", {}, n))));
     } catch (error) {
       render($("#list"), errorState(error, load));
     }
   }

   load();
   ```
4. **Style it** if needed: add rules to `css/pages.css` under a
   `/* ---- Companies ---- */` comment. Use variables from `tokens.css`.
5. **Refresh the browser.** No build step.

## Accessibility built in

- Every page has a "Skip to content" link (press Tab once).
- All controls work with the keyboard; focus is always visible.
- Dialogs use the browser's `<dialog>`, which traps focus and closes on Esc.
- Status is never shown by color alone: badges have an icon and a word.
- The chart has a hidden table version for screen readers.
- Toasts are announced (`aria-live`).
- Motion is reduced when the system asks for it.

Next: [04 Design system](04-design-system.md)
