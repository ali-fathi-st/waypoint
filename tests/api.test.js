import { test } from "node:test";
import assert from "node:assert/strict";
import { combineApis } from "../frontend/js/api/api.js";
import { createMockApi } from "../frontend/js/api/mock-api.js";

test("hybrid mode sends listed operations to the backend and the rest to the mock", async () => {
  const mock = createMockApi({
    storage: null,
    latencyMs: 0,
    scenario: "normal",
  });
  const backend = {
    listJobs: async () => ({ items: [], total: 0, limit: 20, offset: 0 }),
  };
  const api = combineApis(mock, backend, ["listJobs"]);
  assert.equal(api.mode, "hybrid");
  assert.equal((await api.listJobs()).total, 0); // from the "backend"
  assert.ok((await api.listApplications()).length > 0); // from the mock
});

test("a misspelled operation name fails loudly", () => {
  const mock = createMockApi({ storage: null, latencyMs: 0 });
  assert.throws(
    () => combineApis(mock, mock, ["listJob"]),
    /unknown names: listJob/,
  );
});
