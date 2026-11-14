// The HTTP API is tested with a fake fetch, so no backend is needed.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHttpApi } from "../frontend/js/api/http-api.js";
import { createMockDatabase } from "../frontend/js/data/sample-data.js";

const db = createMockDatabase(new Date(2026, 10, 10));

function fakeFetch(status, body) {
  const calls = [];
  const fn = async (url, init) => {
    calls.push({ url, init });
    return new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  };
  return { fn, calls };
}

test("builds /api/v1 URLs and leaves out empty filters", async () => {
  const { fn, calls } = fakeFetch(200, {
    items: [db.jobs[0]],
    total: 1,
    limit: 20,
    offset: 0,
  });
  const api = createHttpApi("http://api.test/", fn);
  await api.listJobs({ q: "data", company: "", limit: 20 });
  const url = new URL(calls[0].url);
  assert.equal(url.origin + url.pathname, "http://api.test/api/v1/jobs");
  assert.equal(url.searchParams.get("q"), "data");
  assert.equal(url.searchParams.has("company"), false);
});

test("sends JSON with the login cookie", async () => {
  const { fn, calls } = fakeFetch(200, db.applications[0]);
  await createHttpApi("http://api.test", fn).updateApplication("app_001", {
    notes: "hi",
  });
  assert.equal(calls[0].init.method, "PATCH");
  assert.equal(calls[0].init.credentials, "include");
  assert.deepEqual(JSON.parse(calls[0].init.body), { notes: "hi" });
});

test("reads FastAPI validation errors field by field", async () => {
  const { fn } = fakeFetch(422, {
    detail: [
      { loc: ["body", "follow_up_at"], msg: "Input should be a valid date" },
    ],
  });
  const err = await createHttpApi("http://api.test", fn)
    .updateApplication("a", {})
    .catch((e) => e);
  assert.equal(err.code, "validation");
  assert.equal(err.fieldErrors.follow_up_at, "Input should be a valid date");
});

test("404 becomes 'not found' with the backend's message", async () => {
  const { fn } = fakeFetch(404, { detail: "Job not found" });
  const err = await createHttpApi("http://api.test", fn)
    .getJob("x")
    .catch((e) => e);
  assert.equal(err.code, "not_found");
  assert.equal(err.message, "Job not found");
});

test("names the missing field when the backend's data is incomplete", async () => {
  const { first_seen_at, ...broken } = db.jobs[0];
  assert.ok(first_seen_at);
  const { fn } = fakeFetch(200, broken);
  const err = await createHttpApi("http://api.test", fn)
    .getJob("x")
    .catch((e) => e);
  assert.equal(err.code, "contract");
  assert.match(err.message, /first_seen_at/);
});

test("reports a backend that can't be reached", async () => {
  const api = createHttpApi("http://api.test", async () => {
    throw new TypeError("fetch failed");
  });
  const err = await api.getSettings().catch((e) => e);
  assert.equal(err.code, "network");
});
