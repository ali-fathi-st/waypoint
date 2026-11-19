# 7. Connecting the backend

The site uses built-in sample data until you point it at the FastAPI server.
This guide covers the switch, without touching any page code.

**The quickest way: Settings → Developer → Your backend → Connect.** It
points your browser at your backend without changing any file, so the
published site keeps showing sample data to everyone else. Setup:
[09 The backend](09-backend.md#3-point-the-website-at-it).

Editing `config.js` (below) changes where data comes from for *every*
visitor. Use it to connect operations one at a time while you build new ones,
or once a hosted backend exists.

## The switch: frontend/js/config.js

```js
export const config = {
  apiMode: "mock", // "mock" | "http" | "hybrid"
  apiBaseUrl: "", // e.g. "http://localhost:8000"
  liveOperations: [], // only for "hybrid", e.g. ["listJobs", "getJob"]
};
```

| apiMode | Where data comes from |
| --- | --- |
| `"mock"` | Sample data in your browser. The default; what GitHub Pages runs. |
| `"http"` | Every operation goes to `apiBaseUrl`. |
| `"hybrid"` | Operations in `liveOperations` go to the backend; the rest use sample data. |

The sidebar always says which one is active, and **Settings → Developer**
shows the details.

## Recommended path: one endpoint at a time

1. **Build one endpoint** in FastAPI, following [06 API contract](06-api-contract.md).
   Start with `GET /api/v1/jobs`.
2. **Allow the site in CORS** (snippet in [06](06-api-contract.md#cors)).
   Include `http://localhost:8080`.
3. **Check it** at `http://localhost:8000/docs` (FastAPI's built-in page).
4. **Switch just that operation:**
   ```js
   export const config = {
     apiMode: "hybrid",
     apiBaseUrl: "http://localhost:8000",
     liveOperations: ["listJobs"],
   };
   ```
5. **Refresh the site.** The sidebar reads "1 operation live from
   http://localhost:8000". The Jobs page now shows your backend's jobs.
6. **If something doesn't match**, the page names it, e.g.
   *`GET /jobs: item 0 is missing "first_seen_at"`*. Fix the backend, refresh.
7. **Add operations** as you build them. A good order:

   | Step | Add to liveOperations | Why this order |
   | --- | --- | --- |
   | 1 | `listJobs`, `getJob` | Read-only, simplest |
   | 2 | `updateJobStatus` | First write |
   | 3 | `getCandidateProfile`, `updateCandidateProfile` | Scores depend on it |
   | 4 | `listApplications`, `getApplication`, `createApplication`, `updateApplication`, `confirmSubmission`, `addInterview` | Move these **together** (see warning) |
   | 5 | `getDashboardMetrics` | Built from the tables above: good SQL practice |
   | 6 | `listDocuments`, `uploadDocument`, `updateDocument` | Needs file storage |
   | 7 | `getSettings`, `updateSettings`, `exportData`, `deleteAllData` | Last |

8. **When everything is live**, set `apiMode: "http"` and empty `liveOperations`.

The valid operation names are listed in `frontend/js/api/api.js`
(`OPERATIONS`). A misspelled name stops the page with an error listing the
valid ones.

> **Move related operations together.** Data written to the sample data stays
> in your browser. If `createApplication` goes to the backend while
> `listApplications` still reads sample data, new applications won't appear
> in the list.

## Where to run things while you build

Run **both on your computer**: the site at `http://localhost:8080` and FastAPI
at `http://localhost:8000`. That avoids every browser restriction.

Don't commit a `config.js` that points at your laptop: every visitor's
browser would try to reach *their own* computer and fail. To use the
published site with your backend, connect your browser from Settings →
Developer instead. Chrome and Edge ask once for permission; Safari blocks
public sites from reaching your computer. A backend other people use must be
hosted on `https://`.

| Where | config.js |
| --- | --- |
| Committed to GitHub (what Pages serves) | `apiMode: "mock"` until a hosted backend exists |
| Your computer while building | `"hybrid"` or `"http"` with `http://localhost:8000` |
| Later, with a hosted backend | `"http"` with `https://your-api.example.com`, and that origin allowed in CORS |

Tip: keep `config.js` on `"mock"` in your commits and change it only on your
computer, so the published site never points at your laptop.

## When something goes wrong

| Message on the page | Likely cause | Fix |
| --- | --- | --- |
| "Can't reach the API..." | Backend not running, wrong `apiBaseUrl`, or CORS blocked it | Start uvicorn; check the URL; open `F12` → Console: a CORS error names the missing origin |
| "...missing "field_name"" | The backend's reply lacks a field | Add it to the Pydantic response model (send `null` rather than leaving it out) |
| "You're not signed in..." | 401/403 from the backend | Expected until sign-in exists; check the route isn't protected yet |
| Field errors under a form field | FastAPI returned 422 | The message comes from Pydantic; adjust the request or the model |
| "This record doesn't exist" | 404 | The id doesn't exist in your database |

## What the frontend needs from the backend, in short

- Same field names as the sample data (snake_case), `null` for empty values.
- Dates as `YYYY-MM-DD`, timestamps as ISO 8601 UTC.
- FastAPI's normal error format (`{"detail": ...}`).
- The rules in [06](06-api-contract.md): one application per job, "applied" only through
  `confirm-submission`, allowed status moves, follow-ups cleared on close.
- CORS allowing the site's origin, with credentials.

Next: [08 Testing](08-testing.md)
