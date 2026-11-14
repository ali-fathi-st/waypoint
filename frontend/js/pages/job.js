/**
 * Job detail (job.html?id=job_001): the posting, how its match score adds
 * up, its skills, and the actions to shortlist, dismiss or start applying.
 */
import { initShell } from "../ui/shell.js";
import { api } from "../api/api.js";
import { isApiError, describeError } from "../api/errors.js";
import { h, render, $, withBusy } from "../lib/dom.js";
import { getParam } from "../lib/url.js";
import { icon } from "../ui/icons.js";
import { toast } from "../ui/toast.js";
import { fitLedger } from "../ui/match.js";
import { jobActions } from "../ui/job-actions.js";
import { jobBadge } from "../ui/badges.js";
import { emptyState, errorState, loadingBlock } from "../ui/states.js";
import { formatDate, formatDateTime, formatSalary } from "../lib/format.js";
import {
  EMPLOYMENT_TYPE_LABEL,
  SOURCE_LABEL,
  WORK_ARRANGEMENT_LABEL,
} from "../lib/status.js";

initShell();
$("#back-link").prepend(icon("back"));

const jobId = getParam("id");

/**
 * Show the description as plain text. Lines starting with "- " become list
 * items; a short line right before a list becomes a subheading.
 */
function descriptionBlocks(text) {
  const bullet = /^[-•*]\s+/;
  return text
    .replace(/\r\n/g, "\n")
    .split(/\n{2,}/)
    .map((block) => {
      const lines = block
        .split("\n")
        .map((l) => l.trim())
        .filter(Boolean);
      const hasHeading =
        lines.length > 1 &&
        !bullet.test(lines[0]) &&
        lines[0].length < 60 &&
        !/[.:]$/.test(lines[0]) &&
        bullet.test(lines[1]);
      const body = hasHeading ? lines.slice(1) : lines;
      const isList = body.length > 0 && body.every((l) => bullet.test(l));
      return h(
        "div",
        {},
        hasHeading ? h("h3", {}, lines[0]) : null,
        isList
          ? h(
              "ul",
              {},
              body.map((l) => h("li", {}, l.replace(bullet, ""))),
            )
          : body.map((l) => h("p", {}, l)),
      );
    });
}

function skillsList(job) {
  if (!job.skills.length)
    return h(
      "p",
      { class: "muted" },
      "No skills were extracted from this posting.",
    );
  const matched = new Set(
    (job.match?.matched_skills ?? []).map((s) => s.toLowerCase()),
  );
  const group = (title, skills) =>
    skills.length
      ? h(
          "div",
          {},
          h("h3", {}, title),
          h(
            "ul",
            {},
            skills.map((s) => {
              const has = matched.has(s.name.toLowerCase());
              return h(
                "li",
                { class: has ? "has" : null },
                icon(has ? "check" : "minus"),
                h(
                  "span",
                  {},
                  s.name,
                  h(
                    "span",
                    { class: "sr-only" },
                    has ? " (on your profile)" : " (not on your profile)",
                  ),
                  s.evidence ? h("small", {}, `“${s.evidence}”`) : null,
                ),
              );
            }),
          ),
        )
      : null;
  const missing = job.match?.missing_skills ?? [];
  return h(
    "div",
    { class: "skills" },
    group(
      "Required",
      job.skills.filter((s) => s.required),
    ),
    group(
      "Nice to have",
      job.skills.filter((s) => !s.required),
    ),
    missing.length
      ? h(
          "div",
          { class: "note note--info" },
          h("strong", { class: "block" }, "Missing from your profile"),
          h("span", { class: "block" }, missing.join(", ")),
          h(
            "span",
            { class: "block small muted" },
            "If you have one of these, add it to your profile and the score updates.",
          ),
        )
      : null,
  );
}

async function startApplication(button, job) {
  await withBusy(button, "Starting...", async () => {
    try {
      const app = await api.createApplication({ job_id: job.id });
      window.location.href = `application.html?id=${encodeURIComponent(app.id)}&started=1`;
    } catch (e) {
      toast.error("Couldn't start the application", describeError(e));
      if (isApiError(e) && e.code === "conflict") load();
    }
  });
}

function renderJob(job) {
  document.title = `${job.title} | Waypoint`;
  $("#job-title").textContent = job.title;
  const salary = formatSalary(
    job.salary_min,
    job.salary_max,
    job.salary_currency,
  );
  render(
    $("#job-meta"),
    h(
      "div",
      { class: "meta ink-2" },
      h("span", {}, job.company.name),
      h("span", {}, job.location ?? "Location not stated"),
      h("span", {}, WORK_ARRANGEMENT_LABEL[job.work_arrangement]),
      h("span", {}, EMPLOYMENT_TYPE_LABEL[job.employment_type]),
      h("span", {}, salary ?? "Salary not posted"),
    ),
    h(
      "div",
      { class: "meta" },
      jobBadge(job.review_status),
      h(
        "span",
        {},
        job.posted_at
          ? `Posted ${formatDate(job.posted_at)}`
          : "Posting date unknown",
      ),
      h(
        "span",
        { title: formatDateTime(job.first_seen_at) },
        `Found ${formatDate(job.first_seen_at)} via ${SOURCE_LABEL[job.source]}`,
      ),
    ),
  );

  const applyButton = job.application_id
    ? h(
        "a",
        {
          class: "btn btn--primary",
          href: `application.html?id=${encodeURIComponent(job.application_id)}`,
        },
        icon("applications"),
        "Open application",
      )
    : h(
        "button",
        {
          type: "button",
          class: "btn btn--primary",
          disabled: job.review_status === "dismissed",
        },
        "Start application",
      );
  if (!job.application_id)
    applyButton.addEventListener("click", () =>
      startApplication(applyButton, job),
    );
  render($("#job-actions"), jobActions(job, { onChange: load }), applyButton);

  const original = $("#original-link");
  original.href = job.url;
  original.hidden = false;
  if (!original.querySelector("svg")) original.prepend(icon("external"));

  render(
    $("#description"),
    h("div", { class: "description" }, descriptionBlocks(job.description)),
  );
  render(
    $("#match"),
    job.match
      ? fitLedger(job.match)
      : emptyState({
          title: "Not scored yet",
          description:
            "Scores are calculated once your profile and this job are both saved.",
        }),
  );
  render($("#skills"), skillsList(job));
}

async function load() {
  render($("#error"));
  if (!jobId) return showNotFound();
  try {
    renderJob(await api.getJob(jobId));
  } catch (error) {
    if (isApiError(error) && error.code === "not_found") return showNotFound();
    if (!isApiError(error)) console.error(error); // a bug, not a network problem
    $("#job-title").textContent = "Job";
    $("#job-body").hidden = true;
    render(
      $("#error"),
      errorState(error, () => {
        $("#job-body").hidden = false;
        load();
      }),
    );
  }
}

function showNotFound() {
  $("#job-title").textContent = "Job not found";
  $("#job-body").hidden = true;
  render(
    $("#error"),
    h(
      "section",
      { class: "panel" },
      emptyState({
        iconName: "file-search",
        title: "This job isn't in your list",
        description:
          "It may have been removed by a source update, or the link is wrong.",
        action: h("a", { class: "btn", href: "jobs.html" }, "Back to jobs"),
      }),
    ),
  );
}

render($("#description"), loadingBlock());
render($("#skills"), loadingBlock());
load();
