/**
 * HTTP API: talks to the FastAPI backend at config.apiBaseUrl.
 *
 * Each function matches one endpoint in docs/06-api-contract.md and returns
 * the same data shape as the mock API, so pages can't tell the difference.
 * Every response is checked for missing fields (see contract.js).
 */
import { ApiError, codeForStatus } from "./errors.js";
import { findMissingField } from "./contract.js";

/** FastAPI error bodies: {"detail": "text"} or {"detail": [{loc, msg}]} */
function readErrorBody(body) {
  const fieldErrors = {};
  const detail = body && typeof body === "object" ? body.detail : null;
  if (typeof detail === "string") return { message: detail, fieldErrors };
  if (Array.isArray(detail)) {
    for (const item of detail) {
      const path = Array.isArray(item?.loc)
        ? item.loc.filter((p) => p !== "body" && p !== "query").join(".")
        : "";
      if (item?.msg) fieldErrors[path || "_"] = String(item.msg);
    }
    const [field, msg] = Object.entries(fieldErrors)[0] ?? [];
    return {
      message: field
        ? `${field !== "_" ? `${field}: ` : ""}${msg}`
        : "Invalid request.",
      fieldErrors,
    };
  }
  return { message: "", fieldErrors };
}

export function createHttpApi(
  baseUrl,
  fetchImpl = (...args) => fetch(...args),
) {
  if (!baseUrl) {
    throw new Error(
      'config.apiBaseUrl is empty. Set it in js/config.js, or use apiMode: "mock".',
    );
  }
  const root = `${baseUrl.replace(/\/+$/, "")}/api/v1`;

  /** Make one request. Returns the Response (already checked for errors). */
  async function send(method, path, { query, body } = {}) {
    const url = new URL(root + path);
    for (const [key, value] of Object.entries(query ?? {})) {
      if (value !== undefined && value !== null && value !== "")
        url.searchParams.set(key, String(value));
    }
    const isForm = body instanceof FormData;
    let response;
    try {
      response = await fetchImpl(url.toString(), {
        method,
        credentials: "include", // sends the login cookie once the backend has sign-in
        headers: {
          Accept: "application/json",
          ...(body !== undefined && !isForm
            ? { "Content-Type": "application/json" }
            : {}),
        },
        body:
          body === undefined ? undefined : isForm ? body : JSON.stringify(body),
      });
    } catch {
      throw new ApiError("Network request failed.", { code: "network" });
    }
    if (!response.ok) {
      let errorBody = null;
      try {
        errorBody = await response.json();
      } catch {
        /* not JSON */
      }
      const { message, fieldErrors } = readErrorBody(errorBody);
      throw new ApiError(message || `Request failed (${response.status}).`, {
        status: response.status,
        code: codeForStatus(response.status),
        fieldErrors,
      });
    }
    return response;
  }

  /** Request JSON and check it has the fields the pages need. */
  async function request(method, path, kind, options) {
    const response = await send(method, path, options);
    let data;
    try {
      data = await response.json();
    } catch {
      throw new ApiError(`${method} ${path} did not return JSON.`, {
        code: "contract",
      });
    }
    const problem = checkShape(kind, data);
    if (problem)
      throw new ApiError(`${method} ${path}: ${problem}.`, {
        code: "contract",
      });
    return data;
  }

  /** kind: "job", "job[]", "page:job", etc. Returns a problem description or null. */
  function checkShape(kind, data) {
    if (kind.startsWith("page:")) {
      const missing = findMissingField("page", data);
      if (missing) return `missing "${missing}"`;
      return checkShape(`${kind.slice(5)}[]`, data.items);
    }
    if (kind.endsWith("[]")) {
      if (!Array.isArray(data)) return "expected a list";
      for (let i = 0; i < data.length; i++) {
        const missing = findMissingField(kind.slice(0, -2), data[i]);
        if (missing) return `item ${i} is missing "${missing}"`;
      }
      return null;
    }
    const missing = findMissingField(kind, data);
    return missing ? `missing "${missing}"` : null;
  }

  const id = (value) => encodeURIComponent(value);

  return {
    mode: "http",

    listJobs: (params = {}) =>
      request("GET", "/jobs", "page:job", { query: params }),
    getJob: (jobId) => request("GET", `/jobs/${id(jobId)}`, "job"),
    updateJobStatus: (jobId, review_status) =>
      request("PATCH", `/jobs/${id(jobId)}`, "job", {
        body: { review_status },
      }),

    listApplications: (params = {}) =>
      request("GET", "/applications", "application[]", { query: params }),
    getApplication: (appId) =>
      request("GET", `/applications/${id(appId)}`, "application"),
    createApplication: (input) =>
      request("POST", "/applications", "application", { body: input }),
    updateApplication: (appId, input) =>
      request("PATCH", `/applications/${id(appId)}`, "application", {
        body: input,
      }),
    confirmSubmission: (appId, input) =>
      request(
        "POST",
        `/applications/${id(appId)}/confirm-submission`,
        "application",
        { body: input },
      ),
    addInterview: (appId, input) =>
      request("POST", `/applications/${id(appId)}/interviews`, "application", {
        body: input,
      }),

    getDashboardMetrics: () => request("GET", "/dashboard/metrics", "metrics"),

    getCandidateProfile: () => request("GET", "/candidate", "profile"),
    updateCandidateProfile: (input) =>
      request("PUT", "/candidate", "profile", { body: input }),

    listDocuments: (params = {}) =>
      request("GET", "/documents", "document[]", { query: params }),
    uploadDocument: (input) => {
      const form = new FormData();
      form.set("document_type", input.document_type);
      form.set("title", input.title);
      if (input.related_job_id)
        form.set("related_job_id", input.related_job_id);
      form.set("file", input.file);
      return request("POST", "/documents", "document", { body: form });
    },
    updateDocument: (docId, input) =>
      request("PATCH", `/documents/${id(docId)}`, "document", { body: input }),

    getSettings: () => request("GET", "/settings", "settings"),
    updateSettings: (input) =>
      request("PATCH", "/settings", "settings", { body: input }),
    exportData: async () => (await send("GET", "/export")).blob(),
    deleteAllData: async () => {
      await send("DELETE", "/data");
    },
  };
}
