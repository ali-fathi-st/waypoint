/**
 * SITE SETTINGS: the only file you edit to connect the backend.
 *
 * apiMode
 *   "mock"   Use the built-in sample data (default). Works on GitHub Pages
 *            with no backend at all.
 *   "http"   Send every request to your FastAPI backend at apiBaseUrl.
 *   "hybrid" Send only the operations listed in liveOperations to the
 *            backend; everything else keeps using sample data. Use this to
 *            connect one endpoint at a time.
 *
 * apiBaseUrl
 *   Where FastAPI runs, without a trailing slash, e.g. "http://localhost:8000".
 *   Routes are under /api/v1 (see docs/06-api-contract.md).
 *
 * liveOperations
 *   Only for "hybrid". Names from js/api/api.js, e.g. ["listJobs", "getJob"].
 *
 * Never put passwords, API keys or database URLs here: everything in this
 * folder is public once it's on GitHub Pages.
 */
export const config = {
  apiMode: "mock",
  apiBaseUrl: "",
  liveOperations: [],
};
