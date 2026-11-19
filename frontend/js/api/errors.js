/**
 * One error type for every API call, whether the data came from the mock or
 * from the backend. Pages show describeError(e) to the user.
 *
 * Codes: network | not_found | validation | conflict | unauthorized | server
 *        | contract (the response had the wrong shape) | unknown
 */
export class ApiError extends Error {
  status;
  code;

  /** Field-level messages from FastAPI's 422 responses, keyed by field path. */
  fieldErrors;
  constructor(message, opts) {
    super(message);
    this.name = "ApiError";
    this.status = opts.status ?? 0;
    this.code = opts.code;
    this.fieldErrors = opts.fieldErrors ?? {};
  }
}

export function isApiError(e) {
  return e instanceof ApiError;
}

export function codeForStatus(status) {
  if (status === 404) return "not_found";
  if (status === 400 || status === 422) return "validation";
  if (status === 409) return "conflict";
  if (status === 401 || status === 403) return "unauthorized";
  if (status >= 500) return "server";
  return "unknown";
}

/** Short, specific text for the UI. */
export function describeError(e) {
  if (!isApiError(e))
    return "Something unexpected went wrong. Reload the page to try again.";
  switch (e.code) {
    case "network":
      return "Can't reach your backend. Check that it's running, or change the connection in Settings > Developer.";
    case "not_found":
      return "This record doesn't exist, or it was deleted.";
    case "unauthorized":
      return "You're not signed in, or your session ended.";
    case "contract":
      return `The API returned data in an unexpected shape. ${e.message}`;
    default:
      return e.message;
  }
}
