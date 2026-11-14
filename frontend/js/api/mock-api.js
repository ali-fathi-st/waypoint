/**
 * MOCK API: behaves like the future FastAPI backend, using sample data.
 *
 * - Data lives in memory and is saved to localStorage, so your changes
 *   survive a reload. Settings > Developer > "Reset sample data" restores it.
 * - It enforces the same rules the backend should: one application per job,
 *   allowed status changes, "applied" only through confirmSubmission, and
 *   "not found" errors for unknown ids. That makes it a working spec for the
 *   Python service.
 * - A scenario switch (normal / empty / slow / error) shows every loading,
 *   empty and error state without changing any code.
 *
 * Every function returns a Promise, exactly like a real network call.
 */
import { ApiError } from "./errors.js";
import {
  createEmptyDatabase,
  createMockDatabase,
  scoreJob,
} from "../data/sample-data.js";
import {
  APPLICATION_STATUS_LABEL,
  FOLLOW_UP_STATUSES,
  SUBMITTED_STATUSES,
  canConfirmSubmission,
  canTransition,
} from "../lib/status.js";
import { formatDate, todayDateOnly, toDateOnly } from "../lib/format.js";

export const MOCK_SCENARIOS = ["normal", "empty", "slow", "error"];

const SCENARIO_KEY = "waypoint.mock-scenario";

const DB_KEY = "waypoint.mock-db.v1";

export const MOCK_SCENARIO_EVENT = "waypoint:mock-scenario";

function browserStorage() {
  try {
    if (typeof window === "undefined") return null;
    const s = window.localStorage;
    const probe = "__waypoint_probe__";
    s.setItem(probe, "1");
    s.removeItem(probe);
    return s;
  } catch {
    return null; // private mode, disabled storage, sandboxed iframe
  }
}

export function getMockScenario() {
  const value = browserStorage()?.getItem(SCENARIO_KEY);
  return MOCK_SCENARIOS.includes(value) ? value : "normal";
}

export function setMockScenario(scenario) {
  browserStorage()?.setItem(SCENARIO_KEY, scenario);
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent(MOCK_SCENARIO_EVENT, { detail: scenario }),
    );
  }
}

let idCounter = 0;

function newId(prefix) {
  idCounter += 1;
  return `${prefix}_${Date.now().toString(36)}${idCounter.toString(36)}`;
}

const clone = (v) => structuredClone(v);

export function createMockApi(options = {}) {
  const now = options.now ?? (() => new Date());
  const storage =
    options.storage === undefined ? browserStorage() : options.storage;
  const scenario = () => options.scenario ?? getMockScenario();
  let db = null;
  let emptyDb = null;

  function load() {
    if (scenario() === "empty") {
      emptyDb ??= createEmptyDatabase(now());
      return emptyDb;
    }
    if (db) return db;
    const saved = storage?.getItem(DB_KEY);
    if (saved) {
      try {
        db = JSON.parse(saved);
        return db;
      } catch {
        storage?.removeItem(DB_KEY);
      }
    }
    db = createMockDatabase(now());
    return db;
  }

  function save() {
    if (scenario() === "empty" || !db) return;
    try {
      storage?.setItem(DB_KEY, JSON.stringify(db));
    } catch {
      // Storage full or unavailable: keep working in memory.
    }
  }

  /** Every call goes through here: latency, simulated failure, cloned output. */
  async function call(fn, mutates = false) {
    const s = scenario();
    const delay = options.latencyMs ?? (s === "slow" ? 2500 : 300);
    if (delay > 0) await new Promise((r) => setTimeout(r, delay));
    if (s === "error") {
      throw new ApiError(
        "The mock API is set to fail every request (Settings → Developer).",
        {
          status: 503,
          code: "server",
        },
      );
    }
    const result = fn(load());
    if (mutates) save();
    return clone(result);
  }

  // ------------------------------------------------------------ helpers
  const notFound = (what) =>
    new ApiError(`${what} not found.`, { status: 404, code: "not_found" });
  const invalid = (message, fieldErrors) =>
    new ApiError(message, { status: 422, code: "validation", fieldErrors });

  function findJob(data, id) {
    const job = data.jobs.find((j) => j.id === id);
    if (!job) throw notFound("Job");
    return job;
  }

  function findApplication(data, id) {
    const app = data.applications.find((a) => a.id === id);
    if (!app) throw notFound("Application");
    return app;
  }

  function checkDocument(data, id, type) {
    if (id == null) return null;
    const doc = data.documents.find((d) => d.id === id);
    if (!doc || doc.document_type !== type) {
      const field =
        type === "resume" ? "resume_document_id" : "cover_letter_document_id";
      throw invalid("Choose a document from your list.", {
        [field]: "Unknown document",
      });
    }
    return doc;
  }

  function addEvent(app, event) {
    const at = now().toISOString();
    app.events.unshift({
      id: newId("evt"),
      application_id: app.id,
      occurred_at: at,
      from_status: event.from_status ?? null,
      to_status: event.to_status ?? null,
      interview: event.interview ?? null,
      event_type: event.event_type,
      summary: event.summary,
    });
    app.updated_at = at;
  }

  function setStatus(app, to, eventType, summary) {
    const from = app.status;
    app.status = to;
    app.status_source = "user";
    addEvent(app, {
      event_type: eventType,
      summary,
      from_status: from,
      to_status: to,
    });
    if (!FOLLOW_UP_STATUSES.includes(to) && app.follow_up_at) {
      app.follow_up_at = null;
      addEvent(app, {
        event_type: "follow_up_set",
        summary: `Follow-up cleared — not needed once the status is ${APPLICATION_STATUS_LABEL[to].toLowerCase()}`,
      });
    }
  }

  function filterJobs(jobs, p) {
    const review = p.review_status ?? "active";
    const q = p.q?.trim().toLowerCase();
    const company = p.company?.trim().toLowerCase();
    const location = p.location?.trim().toLowerCase();
    return jobs.filter((j) => {
      if (review === "active" && j.review_status === "dismissed") return false;
      if (review !== "active" && review !== "all" && j.review_status !== review)
        return false;
      if (q && !j.title.toLowerCase().includes(q)) return false;
      if (company && !j.company.name.toLowerCase().includes(company))
        return false;
      if (location) {
        const remoteHit =
          "remote".includes(location) && j.work_arrangement === "remote";
        if (!remoteHit && !(j.location ?? "").toLowerCase().includes(location))
          return false;
      }
      if (p.source && j.source !== p.source) return false;
      if (p.found_after && j.first_seen_at < p.found_after) return false;
      if (p.min_score != null && (j.match?.score ?? 0) < p.min_score)
        return false;
      return true;
    });
  }

  function sortJobs(jobs, sort = "match") {
    const byNewest = (a, b) => b.first_seen_at.localeCompare(a.first_seen_at);
    return [...jobs].sort((a, b) => {
      if (sort === "newest") return byNewest(a, b);
      if (sort === "posted")
        return (
          (b.posted_at ?? "").localeCompare(a.posted_at ?? "") || byNewest(a, b)
        );
      return (b.match?.score ?? 0) - (a.match?.score ?? 0) || byNewest(a, b);
    });
  }

  function metrics(data) {
    const today = todayDateOnly(now());
    const reachedInterview = (a) =>
      a.status === "interview" ||
      a.status === "offer" ||
      a.events.some(
        (e) =>
          e.to_status === "interview" || e.event_type === "interview_scheduled",
      );
    const submitted = data.applications.filter(
      (a) =>
        SUBMITTED_STATUSES.includes(a.status) ||
        (a.status === "withdrawn" && a.applied_at),
    );
    const responses = submitted.filter(
      (a) =>
        reachedInterview(a) || a.status === "offer" || a.status === "rejected",
    );
    const sevenDaysAgo = new Date(now());
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    const byDay = [];
    for (let i = 13; i >= 0; i--) {
      const d = new Date(now());
      d.setDate(d.getDate() - i);
      const key = toDateOnly(d);
      byDay.push({
        date: key,
        count: data.jobs.filter(
          (j) => toDateOnly(new Date(j.first_seen_at)) === key,
        ).length,
      });
    }
    const activity = data.applications
      .flatMap((a) =>
        a.events.map((e) => ({
          id: e.id,
          occurred_at: e.occurred_at,
          summary: e.summary,
          job_title: a.job.title,
          company_name: a.job.company_name,
          application_id: a.id,
          job_id: a.job_id,
        })),
      )
      .sort((x, y) => y.occurred_at.localeCompare(x.occurred_at))
      .slice(0, 8);
    return {
      total_jobs: data.jobs.length,
      new_jobs_7d: data.jobs.filter(
        (j) => new Date(j.first_seen_at) >= sevenDaysAgo,
      ).length,
      shortlisted_jobs: data.jobs.filter(
        (j) => j.review_status === "shortlisted",
      ).length,
      applications_submitted: submitted.length,
      interviews: data.applications.filter(reachedInterview).length,
      responses: responses.length,
      response_rate: submitted.length
        ? responses.length / submitted.length
        : null,
      follow_ups_due: data.applications.filter(
        (a) =>
          FOLLOW_UP_STATUSES.includes(a.status) &&
          a.follow_up_at &&
          a.follow_up_at <= today,
      ).length,
      jobs_found_by_day: byDay,
      recent_activity: activity,
      jobs_to_review: sortJobs(
        data.jobs.filter((j) => j.review_status === "new"),
        "match",
      ).slice(0, 5),
      generated_at: now().toISOString(),
    };
  }

  // ------------------------------------------------------------ client
  return {
    mode: "mock",

    reset() {
      storage?.removeItem(DB_KEY);
      db = null;
      emptyDb = null;
    },

    listJobs: (params = {}) =>
      call((data) => {
        const limit = params.limit ?? 20;
        const offset = params.offset ?? 0;
        const all = sortJobs(filterJobs(data.jobs, params), params.sort);
        return {
          items: all.slice(offset, offset + limit),
          total: all.length,
          limit,
          offset,
        };
      }),

    getJob: (id) => call((data) => findJob(data, id)),

    updateJobStatus: (id, review_status) =>
      call((data) => {
        const job = findJob(data, id);
        job.review_status = review_status;
        return job;
      }, true),

    listApplications: (params = {}) =>
      call((data) => {
        const q = params.q?.trim().toLowerCase();
        return data.applications
          .filter((a) => !params.status || a.status === params.status)
          .filter(
            (a) =>
              !q ||
              a.job.title.toLowerCase().includes(q) ||
              a.job.company_name.toLowerCase().includes(q),
          )
          .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
      }),

    getApplication: (id) => call((data) => findApplication(data, id)),

    createApplication: (input) =>
      call((data) => {
        const job = findJob(data, input.job_id);
        if (
          job.application_id ||
          data.applications.some((a) => a.job_id === job.id)
        ) {
          throw new ApiError("You already have an application for this job.", {
            status: 409,
            code: "conflict",
          });
        }
        const at = now().toISOString();
        const app = {
          id: newId("app"),
          job_id: job.id,
          job: {
            title: job.title,
            company_name: job.company.name,
            location: job.location,
            url: job.url,
            source: job.source,
          },
          status: "saved",
          status_source: "user",
          applied_at: null,
          follow_up_at: null,
          resume_document_id: null,
          cover_letter_document_id: null,
          notes: input.notes ?? "",
          created_at: at,
          updated_at: at,
          events: [],
        };
        addEvent(app, {
          event_type: "created",
          summary: "Application created",
          to_status: "saved",
        });
        data.applications.unshift(app);
        job.application_id = app.id;
        if (job.review_status === "new") job.review_status = "shortlisted";
        return app;
      }, true),

    updateApplication: (id, input) =>
      call((data) => {
        const app = findApplication(data, id);
        if (input.status !== undefined && input.status !== app.status) {
          if (input.status === "applied") {
            throw invalid(
              "Use the confirm-submission step to mark an application as applied.",
            );
          }
          if (!canTransition(app.status, input.status)) {
            throw invalid(
              `Can't move from ${APPLICATION_STATUS_LABEL[app.status]} to ${APPLICATION_STATUS_LABEL[input.status]}.`,
              { status: "Transition not allowed" },
            );
          }
          setStatus(
            app,
            input.status,
            "status_changed",
            `Status changed to ${APPLICATION_STATUS_LABEL[input.status].toLowerCase()}`,
          );
        }
        if (input.notes !== undefined && input.notes !== app.notes) {
          if (input.notes.length > 5000)
            throw invalid("Notes are limited to 5,000 characters.", {
              notes: "Too long",
            });
          app.notes = input.notes;
          addEvent(app, {
            event_type: "note_updated",
            summary: "Notes updated",
          });
        }
        if (
          input.follow_up_at !== undefined &&
          input.follow_up_at !== app.follow_up_at
        ) {
          if (
            input.follow_up_at &&
            !/^\d{4}-\d{2}-\d{2}$/.test(input.follow_up_at)
          ) {
            throw invalid("Use a valid date.", {
              follow_up_at: "Invalid date",
            });
          }
          if (input.follow_up_at && !FOLLOW_UP_STATUSES.includes(app.status)) {
            throw invalid(
              "Follow-ups are only for applied or interviewing applications.",
              {
                follow_up_at: "Not available for this status",
              },
            );
          }
          app.follow_up_at = input.follow_up_at;
          addEvent(app, {
            event_type: "follow_up_set",
            summary: input.follow_up_at
              ? `Follow-up set for ${formatDate(input.follow_up_at)}`
              : "Follow-up cleared",
          });
        }
        if (
          input.resume_document_id !== undefined &&
          input.resume_document_id !== app.resume_document_id
        ) {
          const doc = checkDocument(data, input.resume_document_id, "resume");
          app.resume_document_id = input.resume_document_id;
          addEvent(app, {
            event_type: "document_linked",
            summary: doc
              ? `Résumé set to "${doc.title}" (v${doc.version})`
              : "Résumé removed",
          });
        }
        if (
          input.cover_letter_document_id !== undefined &&
          input.cover_letter_document_id !== app.cover_letter_document_id
        ) {
          const doc = checkDocument(
            data,
            input.cover_letter_document_id,
            "cover_letter",
          );
          app.cover_letter_document_id = input.cover_letter_document_id;
          addEvent(app, {
            event_type: "document_linked",
            summary: doc
              ? `Cover letter set to "${doc.title}" (v${doc.version})`
              : "Cover letter removed",
          });
        }
        return app;
      }, true),

    confirmSubmission: (id, input) =>
      call((data) => {
        const app = findApplication(data, id);
        if (!canConfirmSubmission(app.status)) {
          throw invalid(
            `This application is already ${APPLICATION_STATUS_LABEL[app.status].toLowerCase()}.`,
          );
        }
        const today = todayDateOnly(now());
        if (input.applied_at > today) {
          throw invalid("The application date can't be in the future.", {
            applied_at: "In the future",
          });
        }
        if (input.follow_up_at && input.follow_up_at < input.applied_at) {
          throw invalid("Follow-up must be on or after the application date.", {
            follow_up_at: "Too early",
          });
        }
        checkDocument(data, input.resume_document_id, "resume");
        checkDocument(data, input.cover_letter_document_id, "cover_letter");
        app.resume_document_id = input.resume_document_id;
        app.cover_letter_document_id = input.cover_letter_document_id;
        app.applied_at = input.applied_at;
        setStatus(
          app,
          "applied",
          "submission_confirmed",
          "You confirmed you submitted this application on the employer's site",
        );
        app.follow_up_at = input.follow_up_at;
        if (input.follow_up_at) {
          addEvent(app, {
            event_type: "follow_up_set",
            summary: `Follow-up set for ${formatDate(input.follow_up_at)}`,
          });
        }
        return app;
      }, true),

    addInterview: (id, input) =>
      call((data) => {
        const app = findApplication(data, id);
        if (app.status !== "applied" && app.status !== "interview") {
          throw invalid(
            "Interviews can be added once an application is applied.",
          );
        }
        if (Number.isNaN(Date.parse(input.scheduled_for))) {
          throw invalid("Enter a valid date and time.", {
            scheduled_for: "Invalid",
          });
        }
        if (app.status === "applied") {
          setStatus(
            app,
            "interview",
            "status_changed",
            "Status changed to interview",
          );
        }
        const label =
          input.format === "onsite"
            ? "On-site"
            : input.format[0].toUpperCase() + input.format.slice(1);
        addEvent(app, {
          event_type: "interview_scheduled",
          summary: `${label} interview scheduled`,
          interview: { ...input },
        });
        return app;
      }, true),

    getDashboardMetrics: () => call(metrics),

    getCandidateProfile: () => call((data) => data.profile),

    updateCandidateProfile: (input) =>
      call((data) => {
        data.profile = {
          ...data.profile,
          ...input,
          updated_at: now().toISOString(),
        };
        // Scores depend on the profile, so recompute them (the backend would too).
        for (const job of data.jobs)
          job.match = scoreJob(job, data.profile, now());
        return data.profile;
      }, true),

    listDocuments: (params = {}) =>
      call((data) =>
        data.documents
          .filter(
            (d) =>
              !params.document_type || d.document_type === params.document_type,
          )
          .filter((d) => params.include_archived || d.status !== "archived")
          .sort(
            (a, b) =>
              a.document_type.localeCompare(b.document_type) ||
              b.version - a.version ||
              b.created_at.localeCompare(a.created_at),
          ),
      ),

    uploadDocument: (input) =>
      call((data) => {
        // Only metadata is kept. The file itself never leaves the browser.
        const at = now().toISOString();
        const job = input.related_job_id
          ? findJob(data, input.related_job_id)
          : null;
        const version =
          Math.max(
            0,
            ...data.documents
              .filter((d) => d.document_type === input.document_type)
              .map((d) => d.version),
          ) + 1;
        const doc = {
          id: newId("doc"),
          document_type: input.document_type,
          title: input.title,
          version,
          status: "ready",
          origin: "uploaded",
          related_job_id: job?.id ?? null,
          related_job_title: job?.title ?? null,
          file_name: input.file.name,
          size_bytes: input.file.size,
          created_at: at,
          updated_at: at,
        };
        data.documents.push(doc);
        return doc;
      }, true),

    updateDocument: (id, input) =>
      call((data) => {
        const doc = data.documents.find((d) => d.id === id);
        if (!doc) throw notFound("Document");
        if (input.title !== undefined) {
          if (!input.title.trim())
            throw invalid("Give this version a name.", { title: "Required" });
          doc.title = input.title.trim();
        }
        if (input.status !== undefined) doc.status = input.status;
        doc.updated_at = now().toISOString();
        return doc;
      }, true),

    getSettings: () => call((data) => data.settings),

    updateSettings: (input) =>
      call((data) => {
        if (input.sources) {
          for (const change of input.sources) {
            const current = data.settings.sources.find(
              (s) => s.source === change.source,
            );
            if (current) {
              current.enabled = change.enabled;
              current.identifiers = change.identifiers;
            }
          }
        }
        if (input.notifications)
          data.settings.notifications = input.notifications;
        if (input.account) data.settings.account = input.account;
        return data.settings;
      }, true),

    exportData: () =>
      call((data) =>
        JSON.stringify({ exported_at: now().toISOString(), ...data }, null, 2),
      ).then((json) => new Blob([json], { type: "application/json" })),

    deleteAllData: () =>
      call((data) => {
        const empty = createEmptyDatabase(now());
        data.jobs = empty.jobs;
        data.applications = empty.applications;
        data.documents = empty.documents;
        data.profile = {
          ...empty.profile,
          full_name: "",
          email: "",
          preferred_titles: [],
          locations: [],
          exclusions: [],
        };
        data.settings = empty.settings;
      }, true),
  };
}
