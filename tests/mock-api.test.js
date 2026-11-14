// The mock API enforces the rules the backend must follow, so these tests
// double as a checklist for the FastAPI service.
import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { createMockApi } from "../frontend/js/api/mock-api.js";
import { ApiError } from "../frontend/js/api/errors.js";
import { findMissingField } from "../frontend/js/api/contract.js";
import { addDays, todayDateOnly } from "../frontend/js/lib/format.js";

const fixedNow = new Date(2026, 10, 10, 21, 0);
const make = (scenario = "normal") =>
  createMockApi({ storage: null, latencyMs: 0, now: () => fixedNow, scenario });

async function rejectsWith(promise, code) {
  await assert.rejects(
    promise,
    (e) => e instanceof ApiError && e.code === code,
  );
}

async function freshApplication(api) {
  const { items } = await api.listJobs({ review_status: "all", limit: 100 });
  return api.createApplication({
    job_id: items.find((j) => !j.application_id).id,
  });
}

describe("sample data matches the API contract", () => {
  test("every record has the fields the pages need", async () => {
    const api = make();
    for (const job of (await api.listJobs({ review_status: "all", limit: 100 }))
      .items)
      assert.equal(findMissingField("job", job), null);
    for (const app of await api.listApplications())
      assert.equal(findMissingField("application", app), null);
    for (const doc of await api.listDocuments({ include_archived: true }))
      assert.equal(findMissingField("document", doc), null);
    assert.equal(
      findMissingField("metrics", await api.getDashboardMetrics()),
      null,
    );
    assert.equal(
      findMissingField("profile", await api.getCandidateProfile()),
      null,
    );
    assert.equal(findMissingField("settings", await api.getSettings()), null);
  });
});

describe("jobs", () => {
  test("dismissed jobs are hidden by default and results sort by score", async () => {
    const { items } = await make().listJobs({ limit: 100 });
    assert.ok(items.every((j) => j.review_status !== "dismissed"));
    const scores = items.map((j) => j.match.score);
    assert.deepEqual(
      scores,
      [...scores].sort((a, b) => b - a),
    );
  });

  test("filters by title, source and minimum score", async () => {
    const { items } = await make().listJobs({
      q: "data engineer",
      source: "greenhouse",
      min_score: 50,
      limit: 100,
    });
    assert.ok(items.length > 0);
    for (const j of items) {
      assert.match(j.title.toLowerCase(), /data engineer/);
      assert.equal(j.source, "greenhouse");
      assert.ok(j.match.score >= 50);
    }
  });

  test("an unknown job is 'not found'", async () => {
    await rejectsWith(make().getJob("nope"), "not_found");
  });

  test("score factor weights add up to 1", async () => {
    const [job] = (await make().listJobs({ limit: 1 })).items;
    const total = job.match.factors.reduce((sum, f) => sum + f.weight, 0);
    assert.ok(Math.abs(total - 1) < 1e-9);
  });
});

describe("applications", () => {
  test("one application per job", async () => {
    const api = make();
    const app = await freshApplication(api);
    assert.equal(app.status, "saved");
    await rejectsWith(
      api.createApplication({ job_id: app.job_id }),
      "conflict",
    );
  });

  test("'applied' can't be set by a normal update", async () => {
    const api = make();
    const app = await freshApplication(api);
    await rejectsWith(
      api.updateApplication(app.id, { status: "applied" }),
      "validation",
    );
  });

  test("moves that skip steps are refused", async () => {
    const api = make();
    const app = await freshApplication(api);
    await rejectsWith(
      api.updateApplication(app.id, { status: "offer" }),
      "validation",
    );
  });

  test("recording as applied sets the date, the follow-up and a history entry", async () => {
    const api = make();
    const app = await freshApplication(api);
    const today = todayDateOnly(fixedNow);
    const done = await api.confirmSubmission(app.id, {
      applied_at: today,
      follow_up_at: addDays(today, 14),
      resume_document_id: "doc_003",
      cover_letter_document_id: null,
    });
    assert.equal(done.status, "applied");
    assert.equal(done.follow_up_at, addDays(today, 14));
    assert.ok(done.events.some((e) => e.event_type === "submission_confirmed"));
  });

  test("future application dates are refused", async () => {
    const api = make();
    const app = await freshApplication(api);
    await rejectsWith(
      api.confirmSubmission(app.id, {
        applied_at: addDays(todayDateOnly(fixedNow), 1),
        follow_up_at: null,
        resume_document_id: null,
        cover_letter_document_id: null,
      }),
      "validation",
    );
  });

  test("closing an application clears its follow-up", async () => {
    const api = make();
    const [applied] = await api.listApplications({ status: "applied" });
    assert.ok(applied.follow_up_at);
    const closed = await api.updateApplication(applied.id, {
      status: "rejected",
    });
    assert.equal(closed.follow_up_at, null);
  });
});

describe("dashboard and scenarios", () => {
  test("response rate = replies / submitted", async () => {
    const m = await make().getDashboardMetrics();
    assert.ok(
      Math.abs(m.response_rate - m.responses / m.applications_submitted) < 1e-9,
    );
    assert.equal(m.jobs_found_by_day.length, 14);
  });

  test("the empty scenario has no data", async () => {
    const api = make("empty");
    assert.equal((await api.listJobs()).total, 0);
    assert.equal((await api.getDashboardMetrics()).response_rate, null);
  });

  test("the error scenario fails every request", async () => {
    await rejectsWith(make("error").listJobs(), "server");
  });
});
