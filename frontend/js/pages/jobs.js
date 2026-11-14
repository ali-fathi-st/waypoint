/**
 * Jobs (jobs.html): searchable, filterable list of job postings.
 * Filters live in the address bar (?q=analyst&min=70), so a filtered view
 * survives a reload and can be bookmarked.
 */
import { initShell } from "../ui/shell.js";
import { api } from "../api/api.js";
import { h, render, $, debounce } from "../lib/dom.js";
import { getParams, setParams } from "../lib/url.js";
import { scoreMeter } from "../ui/match.js";
import { jobActions } from "../ui/job-actions.js";
import { jobBadge } from "../ui/badges.js";
import { icon } from "../ui/icons.js";
import { emptyState, errorState, loadingRows } from "../ui/states.js";
import { formatDateTime, formatRelative, formatSalary } from "../lib/format.js";
import { SOURCE_LABEL, WORK_ARRANGEMENT_LABEL } from "../lib/status.js";

initShell();

const PAGE_SIZE = 20;
const DEFAULTS = {
  q: "",
  company: "",
  location: "",
  status: "active",
  source: "",
  found: "",
  min: "",
  sort: "match",
};
const FIELDS = Object.keys(DEFAULTS);
const form = $("#filters");

// ---- Filter state <-> form <-> address bar ----
let page = Math.max(1, Number(getParams().page) || 1);

function readForm() {
  return Object.fromEntries(
    FIELDS.map((name) => [name, form.elements[name].value.trim()]),
  );
}

function writeForm(values) {
  for (const name of FIELDS)
    form.elements[name].value = values[name] ?? DEFAULTS[name];
}

function activeFilterCount(values) {
  return FIELDS.filter(
    (name) => name !== "sort" && values[name] !== DEFAULTS[name],
  ).length;
}

/** Turn form values into the API's query parameters. */
function toQuery(values) {
  const hours = { "24h": 24, "7d": 24 * 7, "30d": 24 * 30 }[values.found];
  let foundAfter;
  if (hours) {
    const d = new Date();
    d.setMinutes(0, 0, 0); // round to the hour so repeated loads match
    d.setHours(d.getHours() - hours);
    foundAfter = d.toISOString();
  }
  return {
    q: values.q || undefined,
    company: values.company || undefined,
    location: values.location || undefined,
    source: values.source || undefined,
    found_after: foundAfter,
    min_score: values.min ? Number(values.min) : undefined,
    review_status: values.status,
    sort: values.sort,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  };
}

function syncUrl(values) {
  const changed = Object.fromEntries(
    FIELDS.map((name) => [
      name,
      values[name] === DEFAULTS[name] ? "" : values[name],
    ]),
  );
  setParams({ ...changed, page: page > 1 ? page : "" });
}

// ---- Rendering ----
function locationText(job) {
  if (job.work_arrangement === "remote")
    return job.location ? `Remote (${job.location})` : "Remote";
  return job.location ?? "Location not stated";
}

function jobRow(job) {
  const salary = formatSalary(
    job.salary_min,
    job.salary_max,
    job.salary_currency,
  );
  return h(
    "tr",
    {},
    h("td", { class: "stack-lead" }, scoreMeter(job.match?.score)),
    h(
      "td",
      { class: "stack-main" },
      h(
        "a",
        {
          class: "title-link",
          href: `job.html?id=${encodeURIComponent(job.id)}`,
        },
        job.title,
      ),
      h(
        "div",
        { class: "meta" },
        h("span", {}, job.company.name),
        salary ? h("span", {}, salary) : null,
      ),
    ),
    h(
      "td",
      { class: "stack-full ink-2" },
      h("span", { class: "block" }, locationText(job)),
      job.work_arrangement !== "remote"
        ? h(
            "span",
            { class: "small muted" },
            WORK_ARRANGEMENT_LABEL[job.work_arrangement],
          )
        : null,
    ),
    h(
      "td",
      { class: "stack-hide" },
      h(
        "a",
        {
          href: job.url,
          target: "_blank",
          rel: "noopener noreferrer",
          class: "small",
          "aria-label": `Original posting on ${SOURCE_LABEL[job.source]} (opens in a new tab)`,
        },
        SOURCE_LABEL[job.source],
      ),
    ),
    h(
      "td",
      { class: "stack-full muted" },
      h(
        "time",
        {
          datetime: job.first_seen_at,
          title: formatDateTime(job.first_seen_at),
        },
        `Found ${formatRelative(job.first_seen_at).toLowerCase()}`,
      ),
    ),
    h("td", { class: "stack-full" }, jobBadge(job.review_status)),
    h(
      "td",
      { class: "actions stack-end" },
      jobActions(job, { compact: true, onChange: load }),
    ),
  );
}

function renderResults(result, values) {
  const { items, total } = result;
  const from = total ? (page - 1) * PAGE_SIZE + 1 : 0;
  const to = Math.min(total, page * PAGE_SIZE);
  $("#results-count").textContent = total
    ? `${from}–${to} of ${total} jobs`
    : "No jobs";

  if (!items.length) {
    const filtered = activeFilterCount(values) > 0;
    render(
      $("#results"),
      filtered
        ? emptyState({
            iconName: "search-x",
            title: "No jobs match these filters",
            description:
              "Try a lower match score or a longer date range, or clear the filters.",
            action: h(
              "button",
              { type: "button", class: "btn", onclick: clearFilters },
              "Clear filters",
            ),
          })
        : emptyState({
            iconName: "search-x",
            title: "No jobs yet",
            description:
              "Jobs appear after your sources run. Check which sources are on in Settings.",
            action: h(
              "a",
              { class: "btn", href: "settings.html" },
              "Open settings",
            ),
          }),
    );
    $("#pagination").hidden = true;
    return;
  }

  render(
    $("#results"),
    h(
      "div",
      { class: "table-wrap" },
      h(
        "table",
        { class: "table table--stack" },
        h(
          "thead",
          {},
          h(
            "tr",
            {},
            h("th", { scope: "col" }, "Match"),
            h("th", { scope: "col" }, "Job"),
            h("th", { scope: "col" }, "Location"),
            h("th", { scope: "col" }, "Source"),
            h("th", { scope: "col" }, "Found"),
            h("th", { scope: "col" }, "Status"),
            h(
              "th",
              { scope: "col", class: "actions" },
              h("span", { class: "sr-only" }, "Actions"),
            ),
          ),
        ),
        h("tbody", {}, items.map(jobRow)),
      ),
    ),
  );

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  $("#pagination").hidden = pages <= 1;
  $("#page-label").textContent = `Page ${page} of ${pages}`;
  $("#prev-page").disabled = page <= 1;
  $("#next-page").disabled = page >= pages;
}

// ---- Loading ----
let requestId = 0;
async function load() {
  const values = readForm();
  syncUrl(values);
  $("#clear-filters").hidden = activeFilterCount(values) === 0;
  render($("#error"));
  const thisRequest = ++requestId;
  if (!$("#results").children.length) render($("#results"), loadingRows(8));
  try {
    const result = await api.listJobs(toQuery(values));
    if (thisRequest !== requestId) return; // a newer search started meanwhile
    renderResults(result, values);
  } catch (error) {
    if (thisRequest !== requestId) return;
    $("#results-count").textContent = "";
    render($("#results"));
    render($("#error"), errorState(error, load));
  }
}

function clearFilters() {
  writeForm(DEFAULTS);
  page = 1;
  load();
}

// ---- Events ----
const reloadFromFirstPage = () => {
  page = 1;
  load();
};
form.addEventListener("submit", (e) => e.preventDefault());
for (const select of form.querySelectorAll("select"))
  select.addEventListener("change", reloadFromFirstPage);
const typed = debounce(reloadFromFirstPage, 300);
for (const input of form.querySelectorAll("input"))
  input.addEventListener("input", typed);

$("#clear-filters").addEventListener("click", clearFilters);
$("#prev-page").addEventListener("click", () => {
  page -= 1;
  load();
  $("#main").scrollIntoView();
});
$("#next-page").addEventListener("click", () => {
  page += 1;
  load();
  $("#main").scrollIntoView();
});

// Phones: secondary filters hide behind a toggle (always visible on wider screens).
const toggle = $("#filters-toggle");
function setExpanded(expanded) {
  form.dataset.collapsed = String(!expanded);
  toggle.setAttribute("aria-expanded", String(expanded));
  toggle.replaceChildren(
    icon("filter"),
    expanded ? "Fewer filters" : "More filters",
  );
}
toggle.addEventListener("click", () =>
  setExpanded(form.dataset.collapsed === "true"),
);

// ---- Start ----
const initial = { ...DEFAULTS, ...getParams() };
writeForm(initial);
setExpanded(
  FIELDS.some(
    (name) => !["q", "sort"].includes(name) && initial[name] !== DEFAULTS[name],
  ),
);
load();
