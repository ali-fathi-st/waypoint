/**
 * WHERE THE DATA COMES FROM, for this browser.
 *
 * Normally that's js/config.js (sample data on GitHub Pages). But you can
 * point YOUR browser at your own backend from Settings > Developer, without
 * editing or committing anything: the address is saved in this browser only.
 * Everyone else who opens the site still sees the sample data.
 *
 * Only an address is saved here, never a password or key.
 */
import { config } from "./config.js";

const KEY = "waypoint.backend-url";

function storage() {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null; // private mode or storage disabled
  }
}

/**
 * Checks an address typed by the user. Returns the cleaned address, or throws
 * an Error with a message to show. Plain http is only allowed for this
 * computer; anything else must be https.
 */
export function cleanBackendUrl(input) {
  let url;
  try {
    url = new URL(String(input ?? "").trim());
  } catch {
    throw new Error("Enter a web address, like http://localhost:8000.");
  }
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  if (url.protocol !== "https:" && !(url.protocol === "http:" && local)) {
    throw new Error(
      "Use https://, or http:// only for this computer (localhost).",
    );
  }
  if (url.username || url.password || url.search || url.hash) {
    throw new Error("Enter just the address, without a login or extra parts.");
  }
  return url.origin + url.pathname.replace(/\/+$/, "");
}

/** The settings in effect: a backend saved in this browser wins over config.js. */
export function resolveConnection(base = config, store = storage()) {
  const saved = store?.getItem(KEY);
  if (saved) {
    try {
      return {
        apiMode: "http",
        apiBaseUrl: cleanBackendUrl(saved),
        liveOperations: [],
        source: "browser",
      };
    } catch {
      store.removeItem(KEY); // something invalid was saved: ignore it
    }
  }
  return { ...base, source: "config" };
}

export const connection = resolveConnection();

export function saveBackendUrl(url, store = storage()) {
  const clean = cleanBackendUrl(url);
  store?.setItem(KEY, clean);
  return clean;
}

export function forgetBackendUrl(store = storage()) {
  store?.removeItem(KEY);
}

/**
 * Checks the backend answers. Resolves to true, or throws an Error saying
 * what to fix. Chrome may first ask you to allow this site to reach "apps
 * and services on this device": choose Allow.
 */
export async function testBackend(url, fetchImpl = (...a) => fetch(...a)) {
  const clean = cleanBackendUrl(url);
  let response;
  try {
    response = await fetchImpl(`${clean}/health`, { cache: "no-store" });
  } catch {
    throw new Error(
      "Couldn't reach it. Check the backend is running (uvicorn), that this site's address is in CORS_ORIGINS, and that you allowed access if your browser asked.",
    );
  }
  let body = null;
  try {
    body = await response.json();
  } catch {
    /* not JSON */
  }
  if (!response.ok || body?.status !== "ok") {
    throw new Error(
      `Something answered, but it isn't the Waypoint backend (status ${response.status}).`,
    );
  }
  return true;
}
