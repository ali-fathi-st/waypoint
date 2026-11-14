/**
 * Dashboard (index.html): summary numbers, jobs worth reviewing, a chart of
 * jobs found per day, and recent activity.
 */
import { initShell } from "../ui/shell.js";
import { api } from "../api/api.js";
import { h, render, $ } from "../lib/dom.js";
import { scoreMeter } from "../ui/match.js";
import { jobActions } from "../ui/job-actions.js";
import { barChart } from "../ui/chart.js";
import { emptyState, errorState, loadingRows } from "../ui/states.js";
import {
  formatDateTime,
  formatPercent,
  formatRelative,
  formatShortDate,
} from "../lib/format.js";
import { WORK_ARRANGEMENT_LABEL } from "../lib/status.js";

initShell();

// ---- "How Waypoint works" guide: shown until the user hides it ----
const HOWTO_KEY = "waypoint.howto-hidden";
const howto = $("#howto");
try {
  howto.hidden = localStorage.getItem(HOWTO_KEY) === "1";
} catch {
  howto.hidden = false;
}
$("#howto-hide").addEventListener("click", () => {
  howto.hidden = true;
  try {
    localStorage.setItem(HOWTO_KEY, "1");
  } catch {
    /* storage unavailable: hide for this visit only */
  }
});

// ---- Rendering ----
function stat({ label, value, note, href, alert }) {
  const tag = href ? "a" : "div";
  return h(
    tag,
    { class: `stat${alert ? " stat--alert" : ""}`, href: href ?? null },
    h("p", { class: "stat__label" }, label),
    h("p", { class: "stat__value" }, String(value)),
    note ? h("p", { class: "stat__note" }, note) : null,
  );
}

function renderStats(m) {
  $("#stats").hidden = false;
  render(
    $("#stats"),
    stat({
      label: "Jobs found",
      value: m.total_jobs,
      note: `${m.new_jobs_7d} in the last 7 days`,
      href: "jobs.html",
    }),
    stat({
      label: "Shortlisted",
      value: m.shortlisted_jobs,
      href: "jobs.html?status=shortlisted",
    }),
    stat({
      label: "Applications submitted",
      value: m.applications_submitted,
      href: "applications.html",
    }),
    stat({
      label: "Interviews",
      value: m.interviews,
      href: "applications.html?status=interview",
    }),
    stat({
      label: "Response rate",
      value: formatPercent(m.response_rate),
      note: m.applications_submitted
        ? `${m.responses} of ${m.applications_submitted} replied`
        : "Nothing submitted yet",
    }),
    stat({
      label: "Follow-ups due",
      value: m.follow_ups_due,
      note: m.follow_ups_due ? "Today or overdue" : "None due",
      href: "applications.html?due=1",
      alert: m.follow_ups_due > 0,
    }),
  );
}

function renderToReview(jobs) {
  if (!jobs.length) {
    render(
      $("#to-review"),
      emptyState({
        iconName: "jobs",
        title: "You're caught up",
        description:
          "No unreviewed jobs right now. New postings appear here after your sources run.",
      }),
    );
    return;
  }
  render(
    $("#to-review"),
    h(
      "ul",
      { class: "list" },
      jobs.map((job) =>
        h(
          "li",
          { class: "job-row" },
          scoreMeter(job.match?.score),
          h(
            "div",
            { class: "job-row__main" },
            h(
              "a",
              {
                class: "title-link truncate block",
                href: `job.html?id=${encodeURIComponent(job.id)}`,
              },
              job.title,
            ),
            h(
              "div",
              { class: "meta" },
              h("span", {}, job.company.name),
              h(
                "span",
                {},
                job.location ?? WORK_ARRANGEMENT_LABEL[job.work_arrangement],
              ),
              h(
                "span",
                {},
                `Found ${formatRelative(job.first_seen_at).toLowerCase()}`,
              ),
            ),
          ),
          jobActions(job, { compact: true, onChange: load }),
        ),
      ),
    ),
  );
}

function renderActivity(items) {
  if (!items.length) {
    render(
      $("#activity"),
      emptyState({
        title: "No activity yet",
        description: "Changes to your applications show up here.",
      }),
    );
    return;
  }
  render(
    $("#activity"),
    h(
      "ol",
      { class: "list" },
      items.map((item) =>
        h(
          "li",
          {},
          h(
            "a",
            {
              href: `application.html?id=${encodeURIComponent(item.application_id)}`,
              class: "title-link small truncate block",
            },
            item.job_title,
            item.company_name
              ? h(
                  "span",
                  { class: "muted weight-normal" },
                  `, ${item.company_name}`,
                )
              : null,
          ),
          h("p", { class: "small ink-2" }, item.summary),
          h(
            "time",
            {
              class: "small muted",
              datetime: item.occurred_at,
              title: formatDateTime(item.occurred_at),
            },
            formatRelative(item.occurred_at),
          ),
        ),
      ),
    ),
  );
}

// ---- Loading ----
async function load() {
  render($("#error"));
  try {
    const metrics = await api.getDashboardMetrics();
    renderStats(metrics);
    renderToReview(metrics.jobs_to_review);
    renderActivity(metrics.recent_activity);
    if (metrics.total_jobs === 0) {
      render(
        $("#chart"),
        emptyState({
          title: "No jobs collected yet",
          description:
            "Turn on a source in Settings to start collecting postings.",
        }),
      );
    } else {
      barChart(
        $("#chart"),
        metrics.jobs_found_by_day.map((d) => ({
          label: formatShortDate(d.date),
          value: d.count,
        })),
        { unit: "jobs found" },
      );
    }
  } catch (error) {
    render($("#error"), errorState(error, load));
    $("#stats").hidden = true;
    render($("#to-review"));
    render($("#chart"));
    render($("#activity"));
  }
}

render($("#to-review"), loadingRows(5));
render($("#activity"), loadingRows(6));
render($("#chart"), h("div", { class: "skeleton skeleton--chart" }));
render(
  $("#stats"),
  Array.from({ length: 6 }, () =>
    h(
      "div",
      { class: "stat" },
      h("div", { class: "skeleton skeleton--line skeleton--w50" }),
      h("div", { class: "skeleton skeleton--stat" }),
    ),
  ),
);
load();
