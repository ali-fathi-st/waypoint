/**
 * THE API: every page gets its data through this file and nowhere else.
 *
 * It picks the implementation from js/connection.js (js/config.js, unless
 * this browser was pointed at a backend in Settings > Developer):
 *   mock   -> mock-api.js (sample data in your browser)
 *   http   -> http-api.js (your FastAPI backend)
 *   hybrid -> the operations in config.liveOperations go to the backend,
 *             everything else to the mock
 *
 * Because both implementations have the same functions and return the same
 * shapes, switching needs no page changes.
 */
import { connection } from "../connection.js";
import { createMockApi } from "./mock-api.js";
import { createHttpApi } from "./http-api.js";

/** Every operation, in the order they appear in the API contract. */
export const OPERATIONS = [
  "listJobs",
  "getJob",
  "updateJobStatus",
  "listApplications",
  "getApplication",
  "createApplication",
  "updateApplication",
  "confirmSubmission",
  "addInterview",
  "getDashboardMetrics",
  "getCandidateProfile",
  "updateCandidateProfile",
  "listDocuments",
  "uploadDocument",
  "updateDocument",
  "getSettings",
  "updateSettings",
  "exportData",
  "deleteAllData",
];

/** Route the listed operations to `http`, the rest to `mock`. */
export function combineApis(mock, http, live) {
  const unknown = live.filter((name) => !OPERATIONS.includes(name));
  if (unknown.length) {
    throw new Error(
      `config.liveOperations has unknown names: ${unknown.join(", ")}. Valid names: ${OPERATIONS.join(", ")}`,
    );
  }
  const combined = { ...mock, mode: "hybrid" };
  for (const name of live) combined[name] = http[name];
  return combined;
}

function createApi() {
  const config = connection;
  if (config.apiMode === "http") return createHttpApi(config.apiBaseUrl);
  if (config.apiMode === "hybrid") {
    return combineApis(
      createMockApi(),
      createHttpApi(config.apiBaseUrl),
      config.liveOperations,
    );
  }
  return createMockApi();
}

export const api = createApi();

/** "mock", "http" or "hybrid": pages use it to label where data comes from. */
export const apiMode = api.mode;

/** The mock (when any sample data is in use), for Settings > Developer. */
export const mockApi = api.mode === "http" ? null : api;
