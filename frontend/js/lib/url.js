/**
 * Reading and writing the page's query string (?id=job_001&q=analyst).
 * Relative links plus query strings work the same locally and on GitHub
 * Pages, where the site lives under /<repo-name>/.
 */

/** One query parameter, or null. */
export function getParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

/** All query parameters as a plain object. */
export function getParams() {
  return Object.fromEntries(new URLSearchParams(window.location.search));
}

/**
 * Update the query string without reloading. Empty values are removed, so
 * the URL only shows filters that are actually set.
 */
export function setParams(values) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== null && value !== undefined && value !== "")
      params.set(key, String(value));
  }
  const query = params.toString();
  window.history.replaceState(
    null,
    "",
    query ? `?${query}` : window.location.pathname,
  );
}
