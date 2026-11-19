// The "Your backend" switch: which addresses are accepted, and that a
// backend saved in this browser wins over js/config.js.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  cleanBackendUrl,
  resolveConnection,
  saveBackendUrl,
  forgetBackendUrl,
  testBackend,
} from "../frontend/js/connection.js";

function memoryStorage() {
  const data = new Map();
  return {
    getItem: (k) => (data.has(k) ? data.get(k) : null),
    setItem: (k, v) => data.set(k, String(v)),
    removeItem: (k) => data.delete(k),
  };
}

const base = { apiMode: "mock", apiBaseUrl: "", liveOperations: [] };

test("accepts this computer over http, anything else only over https", () => {
  assert.equal(
    cleanBackendUrl("http://localhost:8000/"),
    "http://localhost:8000",
  );
  assert.equal(
    cleanBackendUrl(" http://127.0.0.1:8000 "),
    "http://127.0.0.1:8000",
  );
  assert.equal(
    cleanBackendUrl("https://api.example.com/"),
    "https://api.example.com",
  );
  assert.throws(() => cleanBackendUrl("http://api.example.com"), /https/);
  assert.throws(() => cleanBackendUrl("localhost:8000"), /web address|https/);
  assert.throws(() => cleanBackendUrl("javascript:alert(1)"), /https/);
  assert.throws(
    () => cleanBackendUrl("https://user:pw@api.example.com"),
    /login/,
  );
});

test("uses config.js until a backend is saved in this browser", () => {
  const store = memoryStorage();
  assert.deepEqual(resolveConnection(base, store), {
    ...base,
    source: "config",
  });
  saveBackendUrl("http://localhost:8000", store);
  assert.deepEqual(resolveConnection(base, store), {
    apiMode: "http",
    apiBaseUrl: "http://localhost:8000",
    liveOperations: [],
    source: "browser",
  });
  forgetBackendUrl(store);
  assert.equal(resolveConnection(base, store).apiMode, "mock");
});

test("an invalid saved address is ignored and removed", () => {
  const store = memoryStorage();
  store.setItem("waypoint.backend-url", "http://evil.example");
  assert.equal(resolveConnection(base, store).apiMode, "mock");
  assert.equal(store.getItem("waypoint.backend-url"), null);
});

test("testBackend checks it's really Waypoint", async () => {
  const ok = async () => ({
    ok: true,
    status: 200,
    json: async () => ({ status: "ok" }),
  });
  const other = async () => ({
    ok: true,
    status: 200,
    json: async () => ({ hello: 1 }),
  });
  const down = async () => {
    throw new TypeError("Failed to fetch");
  };
  assert.equal(await testBackend("http://localhost:8000", ok), true);
  await assert.rejects(
    testBackend("http://localhost:8000", other),
    /isn't the Waypoint backend/,
  );
  await assert.rejects(
    testBackend("http://localhost:8000", down),
    /Couldn't reach it/,
  );
});
