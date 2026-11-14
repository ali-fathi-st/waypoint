/**
 * Applications (applications.html): every application as a board (one
 * column per status) or a table. Filters: search, status, follow-ups due.
 * The view and filters are kept in the address bar.
 */
import { initShell } from "../ui/shell.js";
import { api } from "../api/api.js";
import { h, render, $, $$ } from "../lib/dom.js";
import { getParams, setParams } from "../lib/url.js";
import { applicationBadge } from "../ui/badges.js";
import { followUpLabel, followUpState } from "../ui/follow-up.js";
import { statusSelect } from "../ui/status-select.js";
import { emptyState, errorState, loadingRows } from "../ui/states.js";
import { formatDate, formatRelative, formatShortDate } from "../lib/format.js";
import { APPLICATION_STATUSES } from "../lib/status.js";

initShell();

const params = getParams();
const state = {
  view:
    params.view === "table" || params.status || params.due ? "table" : "board",
  q: params.q ?? "",
  status: APPLICATION_STATUSES.includes(params.status) ? params.status : "",
  due: params.due === "1",
};
let applications = [];

// ---- Filtering (done in the browser; the list is small) ----
function filtered() {
  const needle = state.q.trim().toLowerCase();
  return applications.filter((a) => {
    if (state.status && a.status !== state.status) return false;
    if (state.due && !followUpState(a)?.due) return false;
    if (
      needle &&
      !`${a.job.title} ${a.job.company_name}`.toLowerCase().includes(needle)
    )
      return false;
    return true;
  });
}

function link(app) {
  return h(
    "a",
    {
      class: "title-link",
      href: `application.html?id=${encodeURIComponent(app.id)}`,
    },
    app.job.title,
  );
}

// ---- Board ----
function boardCard(app) {
  return h(
    "li",
    { class: "board__card" },
    link(app),
    h("p", { class: "small muted truncate" }, app.job.company_name),
    h(
      "div",
      { class: "small muted" },
      h(
        "p",
        {},
        app.applied_at
          ? `Applied ${formatShortDate(app.applied_at)}`
          : `Added ${formatRelative(app.created_at).toLowerCase()}`,
      ),
      followUpLabel(app),
    ),
    statusSelect(app, { onChange: load, small: true }),
  );
}

function board(list) {
  return h(
    "div",
    {
      class: "board",
      tabindex: "0",
      "aria-label": "Applications board. Scrolls sideways.",
    },
    h(
      "div",
      { class: "board__columns" },
      APPLICATION_STATUSES.map((status) => {
        const items = list.filter((a) => a.status === status);
        return h(
          "section",
          { class: "board__column", "aria-labelledby": `col-${status}` },
          h(
            "h2",
            { id: `col-${status}` },
            applicationBadge(status),
            h(
              "span",
              { class: "small muted" },
              String(items.length),
              h("span", { class: "sr-only" }, " applications"),
            ),
          ),
          items.length
            ? h("ul", {}, items.map(boardCard))
            : h("p", { class: "board__none" }, "None"),
        );
      }),
    ),
  );
}

// ---- Table ----
function table(list) {
  return h(
    "section",
    { class: "panel" },
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
            ["Job", "Status", "Applied", "Next follow-up", "Last change"].map(
              (t) => h("th", { scope: "col" }, t),
            ),
            h(
              "th",
              { scope: "col", class: "actions" },
              h("span", { class: "sr-only" }, "Change status"),
            ),
          ),
        ),
        h(
          "tbody",
          {},
          list.map((app) =>
            h(
              "tr",
              {},
              h(
                "td",
                { class: "stack-main" },
                link(app),
                h(
                  "div",
                  { class: "meta" },
                  h("span", {}, app.job.company_name),
                  app.job.location ? h("span", {}, app.job.location) : null,
                ),
              ),
              h("td", { class: "stack-full" }, applicationBadge(app.status)),
              h(
                "td",
                { class: "stack-full ink-2" },
                app.applied_at
                  ? [
                      h("span", { class: "stack-only" }, "Applied "),
                      formatDate(app.applied_at),
                    ]
                  : h("span", { class: "muted" }, "Not applied yet"),
              ),
              h(
                "td",
                { class: "stack-full" },
                followUpLabel(app) ??
                  h("span", { class: "muted stack-hide" }, "None"),
              ),
              h(
                "td",
                { class: "stack-hide muted" },
                formatRelative(app.updated_at),
              ),
              h(
                "td",
                { class: "actions stack-full" },
                statusSelect(app, { onChange: load, small: true }),
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

// ---- Page ----
function draw() {
  setParams({
    view: state.view === "table" ? "table" : "",
    q: state.q,
    status: state.status,
    due: state.due ? "1" : "",
  });
  for (const tab of $$("[role=tab]"))
    tab.setAttribute("aria-selected", String(tab.dataset.view === state.view));
  $("#results").setAttribute("aria-labelledby", `tab-${state.view}`);
  $("#f-due").setAttribute("aria-pressed", String(state.due));

  if (!applications.length) {
    render(
      $("#results"),
      h(
        "section",
        { class: "panel" },
        emptyState({
          iconName: "applications",
          title: "No applications yet",
          description:
            "Open a job and choose Start application. It appears here as Saved.",
          action: h(
            "a",
            { class: "btn btn--primary", href: "jobs.html" },
            "Browse jobs",
          ),
        }),
      ),
    );
    return;
  }

  const list = filtered();
  if (!list.length) {
    render(
      $("#results"),
      h(
        "section",
        { class: "panel" },
        emptyState({
          iconName: "search-x",
          title: state.due ? "No follow-ups due" : "No applications match",
          description: state.due
            ? "Nothing needs a follow-up today."
            : "Try another search or status.",
          action: h(
            "button",
            { type: "button", class: "btn", onclick: clearFilters },
            "Clear filters",
          ),
        }),
      ),
    );
    return;
  }
  render($("#results"), state.view === "board" ? board(list) : table(list));
}

function clearFilters() {
  state.q = "";
  state.status = "";
  state.due = false;
  $("#f-q").value = "";
  $("#f-status").value = "";
  draw();
}

async function load() {
  render($("#error"));
  if (!applications.length)
    render($("#results"), h("section", { class: "panel" }, loadingRows(5)));
  try {
    applications = await api.listApplications();
    draw();
  } catch (error) {
    render($("#results"));
    render($("#error"), errorState(error, load));
  }
}

// ---- Events ----
for (const tab of $$("[role=tab]")) {
  tab.addEventListener("click", () => {
    state.view = tab.dataset.view;
    draw();
  });
}
$("#filters").addEventListener("submit", (e) => e.preventDefault());
$("#f-q").addEventListener("input", (e) => {
  state.q = e.target.value;
  draw();
});
$("#f-status").addEventListener("change", (e) => {
  state.status = e.target.value;
  draw();
});
$("#f-due").addEventListener("click", () => {
  state.due = !state.due;
  draw();
});

$("#f-q").value = state.q;
$("#f-status").value = state.status;
load();
