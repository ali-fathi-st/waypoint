/**
 * Application detail (application.html?id=app_001): status, timeline,
 * notes, materials, follow-up and interviews, plus the "Record as applied"
 * confirmation, the only way an application becomes Applied.
 *
 * Links can open the confirmation directly with ?confirm=1.
 */
import { initShell } from "../ui/shell.js";
import { api } from "../api/api.js";
import { describeError, isApiError } from "../api/errors.js";
import { h, render, $, withBusy } from "../lib/dom.js";
import { getParam, setParams } from "../lib/url.js";
import { icon } from "../ui/icons.js";
import { toast } from "../ui/toast.js";
import { setupDialog } from "../ui/dialog.js";
import { applicationBadge } from "../ui/badges.js";
import { followUpLabel } from "../ui/follow-up.js";
import { statusSelect } from "../ui/status-select.js";
import { emptyState, errorState, loadingBlock } from "../ui/states.js";
import {
  addDays,
  formatDate,
  formatDateTime,
  formatRelative,
  todayDateOnly,
} from "../lib/format.js";
import {
  DEFAULT_FOLLOW_UP_DAYS,
  FOLLOW_UP_STATUSES,
  SOURCE_LABEL,
  canConfirmSubmission,
} from "../lib/status.js";

initShell();
$("#back-link").prepend(icon("back"));
for (const close of document.querySelectorAll(".dialog__close"))
  close.append(icon("close"));

const appId = getParam("id");
let app = null; // the application as last loaded
let documents = []; // résumés and cover letters, for the pickers

// =============================================================== rendering

const TIMELINE_ICON = {
  created: "plus",
  status_changed: "dot",
  submission_confirmed: "send",
  note_updated: "pencil",
  follow_up_set: "calendar-plus",
  document_linked: "file",
  interview_scheduled: "calendar",
};

/** Fill a <select> with "None" plus every non-archived document of one type. */
function fillDocumentSelect(select, type, value) {
  const options = documents.filter(
    (d) =>
      d.document_type === type && (d.status !== "archived" || d.id === value),
  );
  render(
    select,
    h("option", { value: "" }, "None"),
    options.map((d) =>
      h(
        "option",
        { value: d.id },
        `${d.title} (v${d.version}${d.status === "draft" ? ", draft" : d.status === "archived" ? ", archived" : ""})`,
      ),
    ),
  );
  select.value = value ?? "";
}

function renderHeader() {
  document.title = `${app.job.title} | Waypoint`;
  $("#app-title").textContent = app.job.title;
  render(
    $("#app-meta"),
    h(
      "div",
      { class: "meta ink-2" },
      h("span", {}, app.job.company_name),
      app.job.location ? h("span", {}, app.job.location) : null,
    ),
    h(
      "div",
      { class: "meta" },
      applicationBadge(app.status),
      h(
        "span",
        {},
        app.status_source === "integration"
          ? "Status confirmed by an integration"
          : "Status set by you",
      ),
      h(
        "span",
        {},
        app.applied_at
          ? `Applied ${formatDate(app.applied_at)}`
          : `Started ${formatDate(app.created_at)}`,
      ),
      followUpLabel(app),
    ),
  );
  render(
    $("#app-actions"),
    statusSelect(app, { onChange: show, onRecordApplied: openConfirm }),
  );
}

function renderNextStep() {
  const show = canConfirmSubmission(app.status);
  $("#next-step").hidden = !show;
  $("#next-step-link").href = app.job.url;
}

function renderTimeline() {
  if (!app.events.length) {
    render($("#timeline"), h("li", { class: "muted" }, "No history yet."));
    return;
  }
  render(
    $("#timeline"),
    app.events.map((e) =>
      h(
        "li",
        {},
        h(
          "span",
          {
            class: `timeline__icon${e.event_type === "submission_confirmed" ? " timeline__icon--key" : ""}`,
          },
          icon(TIMELINE_ICON[e.event_type] ?? "dot"),
        ),
        h(
          "div",
          {},
          h("p", {}, e.summary),
          h(
            "time",
            { datetime: e.occurred_at, title: formatDateTime(e.occurred_at) },
            `${formatRelative(e.occurred_at)}, ${formatDateTime(e.occurred_at).split(", ").pop()}`,
          ),
        ),
      ),
    ),
  );
}

function renderNotes() {
  const notes = $("#notes");
  if (document.activeElement !== notes) notes.value = app.notes;
  updateNotesButtons();
}

function updateNotesButtons() {
  const dirty = $("#notes").value !== app.notes;
  $("#notes-save").disabled = !dirty;
  $("#notes-discard").hidden = !dirty;
}

function renderJobSnapshot() {
  render(
    $("#job-snapshot"),
    h("p", { class: "title-link" }, app.job.title),
    h("p", { class: "ink-2" }, app.job.company_name),
    h("p", { class: "ink-2" }, app.job.location ?? "Location not stated"),
    h("p", { class: "small muted" }, `Source: ${SOURCE_LABEL[app.job.source]}`),
    h(
      "p",
      { class: "row" },
      h(
        "a",
        { href: `job.html?id=${encodeURIComponent(app.job_id)}` },
        "Job details and match",
      ),
      h(
        "a",
        { href: app.job.url, target: "_blank", rel: "noopener noreferrer" },
        "Original posting",
        h("span", { class: "sr-only" }, " (opens in a new tab)"),
      ),
    ),
  );
}

function renderMaterials() {
  // Materials are locked once applied: they record what was actually sent.
  const locked = !canConfirmSubmission(app.status);
  $("#materials-desc").textContent = locked
    ? "The versions you sent."
    : "Versions you plan to send.";
  for (const [id, type, value] of [
    ["#m-resume", "resume", app.resume_document_id],
    ["#m-cover", "cover_letter", app.cover_letter_document_id],
  ]) {
    fillDocumentSelect($(id), type, value);
    $(id).disabled = locked;
  }
  const linked = documents.filter(
    (d) =>
      d.id === app.resume_document_id || d.id === app.cover_letter_document_id,
  );
  $("#draft-warning").hidden = !linked.some((d) => d.status === "draft");
}

function renderFollowUp() {
  const box = $("#followup");
  if (!FOLLOW_UP_STATUSES.includes(app.status)) {
    render(
      box,
      h(
        "p",
        { class: "muted" },
        canConfirmSubmission(app.status)
          ? "A reminder is set when you record the application as applied."
          : "No follow-up needed for a closed application.",
      ),
    );
    return;
  }
  const dateInput = h("input", {
    class: "input",
    type: "date",
    id: "fu-date",
    min: app.applied_at ?? null,
    value: app.follow_up_at ?? "",
  });
  const save = h(
    "button",
    { type: "button", class: "btn btn--primary btn--sm", disabled: true },
    "Save date",
  );
  dateInput.addEventListener(
    "input",
    () =>
      (save.disabled =
        !dateInput.value || dateInput.value === app.follow_up_at),
  );
  save.addEventListener("click", () => updateFollowUp(dateInput.value, save));

  const suggested = app.applied_at
    ? addDays(app.applied_at, DEFAULT_FOLLOW_UP_DAYS)
    : null;
  const suggest =
    suggested && suggested !== app.follow_up_at
      ? h(
          "button",
          {
            type: "button",
            class: "btn btn--sm",
            onclick: (e) => updateFollowUp(suggested, e.currentTarget),
          },
          `${DEFAULT_FOLLOW_UP_DAYS} days after applying`,
        )
      : null;
  const clear = app.follow_up_at
    ? h(
        "button",
        {
          type: "button",
          class: "btn btn--ghost btn--sm",
          onclick: (e) => updateFollowUp(null, e.currentTarget),
        },
        "Clear",
      )
    : null;

  render(
    box,
    followUpLabel(app) ?? h("p", { class: "muted" }, "No reminder set."),
    h(
      "div",
      { class: "field" },
      h("label", { for: "fu-date" }, "Remind me on"),
      dateInput,
    ),
    h("div", { class: "row" }, save, suggest, clear),
  );
}

function renderInterviews() {
  const canAdd = app.status === "applied" || app.status === "interview";
  $("#add-interview").disabled = !canAdd;
  const interviews = app.events
    .filter((e) => e.event_type === "interview_scheduled" && e.interview)
    .sort((a, b) =>
      a.interview.scheduled_for.localeCompare(b.interview.scheduled_for),
    );
  if (!interviews.length) {
    render(
      $("#interviews"),
      h(
        "p",
        { class: "panel__body muted" },
        canAdd
          ? "None scheduled."
          : "Interviews can be added once you've applied.",
      ),
    );
    return;
  }
  const now = new Date().toISOString();
  const FORMAT = { phone: "Phone", video: "Video", onsite: "On-site" };
  render(
    $("#interviews"),
    h(
      "ul",
      { class: "list" },
      interviews.map(({ interview: iv }) =>
        h(
          "li",
          { class: "row" },
          icon("calendar"),
          h(
            "div",
            {},
            h(
              "time",
              { class: "title-link", datetime: iv.scheduled_for },
              formatDateTime(iv.scheduled_for),
            ),
            h(
              "p",
              { class: "small muted" },
              `${FORMAT[iv.format]}${iv.with_whom ? `, with ${iv.with_whom}` : ""}${iv.scheduled_for < now ? " (past)" : ""}`,
            ),
          ),
        ),
      ),
    ),
  );
}

/** Draw everything from the latest `app`. */
function show(updated) {
  if (updated) app = updated;
  renderHeader();
  renderNextStep();
  renderTimeline();
  renderNotes();
  renderJobSnapshot();
  renderMaterials();
  renderFollowUp();
  renderInterviews();
}

// =============================================================== actions

async function updateFollowUp(value, button) {
  await withBusy(button, null, async () => {
    try {
      show(await api.updateApplication(app.id, { follow_up_at: value }));
      toast.success(
        value ? `Follow-up set for ${formatDate(value)}` : "Follow-up cleared",
      );
    } catch (e) {
      toast.error("Couldn't update the follow-up", describeError(e));
    }
  });
}

$("#notes").addEventListener("input", updateNotesButtons);
$("#notes-discard").addEventListener("click", () => {
  $("#notes").value = app.notes;
  updateNotesButtons();
});
$("#notes-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  await withBusy($("#notes-save"), "Saving...", async () => {
    try {
      show(await api.updateApplication(app.id, { notes: $("#notes").value }));
      toast.success("Notes saved");
    } catch (err) {
      toast.error("Couldn't save notes", describeError(err));
    }
  });
  updateNotesButtons();
});

for (const [id, field, label] of [
  ["#m-resume", "resume_document_id", "Résumé"],
  ["#m-cover", "cover_letter_document_id", "Cover letter"],
]) {
  $(id).addEventListener("change", async (e) => {
    try {
      show(
        await api.updateApplication(app.id, {
          [field]: e.target.value || null,
        }),
      );
      toast.success(`${label} updated`);
    } catch (err) {
      toast.error("Couldn't update materials", describeError(err));
      renderMaterials();
    }
  });
}

// ---- Record as applied (the approval step) ----
const confirmDialog = setupDialog($("#confirm-dialog"));
let followUpEdited = false;

function showFieldError(id, message) {
  const el = $(`#${id}-error`);
  el.textContent = message ?? el.textContent;
  el.hidden = !message;
  const input = document.getElementById(id);
  if (message) input.setAttribute("aria-invalid", "true");
  else input.removeAttribute("aria-invalid");
}

function openConfirm() {
  if (!canConfirmSubmission(app.status)) return;
  const today = todayDateOnly();
  followUpEdited = false;
  $("#confirm-posting").href = app.job.url;
  if (!document.querySelector("#confirm-posting svg"))
    $("#confirm-posting").prepend(icon("external"));
  $("#c-applied").value = today;
  $("#c-applied").max = today;
  $("#c-follow").value = addDays(today, DEFAULT_FOLLOW_UP_DAYS);
  fillDocumentSelect($("#c-resume"), "resume", app.resume_document_id);
  fillDocumentSelect(
    $("#c-cover"),
    "cover_letter",
    app.cover_letter_document_id,
  );
  $("#c-reviewed").checked = false;
  $("#c-submitted").checked = false;
  for (const id of ["c-applied", "c-follow"]) showFieldError(id, null);
  for (const id of ["c-reviewed", "c-submitted"]) showFieldError(id, null);
  setParams({ id: app.id, confirm: "1" });
  confirmDialog.showModal();
}

confirmDialog.addEventListener("close", () => setParams({ id: app.id }));
$("#next-step-button").addEventListener("click", openConfirm);

// Keep the follow-up 14 days after the application date until the user changes it.
$("#c-follow").addEventListener("input", () => (followUpEdited = true));
$("#c-applied").addEventListener("input", (e) => {
  if (!followUpEdited && e.target.value)
    $("#c-follow").value = addDays(e.target.value, DEFAULT_FOLLOW_UP_DAYS);
});

$("#confirm-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const applied = $("#c-applied").value;
  const follow = $("#c-follow").value || null;
  const today = todayDateOnly();

  // Validate everything, show every problem at once.
  const errors = {
    "c-applied": !applied
      ? "Enter the date you applied."
      : applied > today
        ? "The date can't be in the future."
        : null,
    "c-follow":
      follow && applied && follow < applied
        ? "Follow-up must be on or after the application date."
        : null,
    "c-reviewed": $("#c-reviewed").checked
      ? null
      : "Confirm you reviewed the materials.",
    "c-submitted": $("#c-submitted").checked
      ? null
      : "Confirm you submitted it on the employer's site.",
  };
  for (const [id, message] of Object.entries(errors))
    showFieldError(id, message);
  const firstProblem = Object.keys(errors).find((id) => errors[id]);
  if (firstProblem) {
    document.getElementById(firstProblem).focus();
    return;
  }

  await withBusy($("#confirm-submit"), "Recording...", async () => {
    try {
      const updated = await api.confirmSubmission(app.id, {
        applied_at: applied,
        follow_up_at: follow,
        resume_document_id: $("#c-resume").value || null,
        cover_letter_document_id: $("#c-cover").value || null,
      });
      confirmDialog.close();
      show(updated);
      toast.success(
        "Recorded as applied",
        follow ? "A follow-up reminder is set." : undefined,
      );
    } catch (err) {
      toast.error("Couldn't record the application", describeError(err));
    }
  });
});

// ---- Add interview ----
const interviewDialog = setupDialog($("#interview-dialog"));
$("#add-interview").addEventListener("click", () => {
  $("#i-date").value = addDays(todayDateOnly(), 1);
  $("#i-time").value = "10:00";
  $("#i-format").value = "video";
  $("#i-with").value = "";
  $("#i-error").hidden = true;
  interviewDialog.showModal();
});
$("#interview-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const date = $("#i-date").value;
  const time = $("#i-time").value;
  if (!date || !time) {
    $("#i-error").textContent = "Enter a date and a time.";
    $("#i-error").hidden = false;
    return;
  }
  const submit = e.submitter ?? e.target.querySelector("[type=submit]");
  await withBusy(submit, "Adding...", async () => {
    try {
      const updated = await api.addInterview(app.id, {
        scheduled_for: new Date(`${date}T${time}`).toISOString(), // your local time, sent as UTC
        format: $("#i-format").value,
        with_whom: $("#i-with").value.trim() || null,
      });
      interviewDialog.close();
      show(updated);
      toast.success("Interview added");
    } catch (err) {
      toast.error("Couldn't add the interview", describeError(err));
    }
  });
});

// =============================================================== loading

function showNotFound() {
  $("#app-title").textContent = "Application not found";
  $("#app-body").hidden = true;
  render(
    $("#error"),
    h(
      "section",
      { class: "panel" },
      emptyState({
        iconName: "file-search",
        title: "This application doesn't exist",
        description: "It may have been deleted, or the link is wrong.",
        action: h(
          "a",
          { class: "btn", href: "applications.html" },
          "Back to applications",
        ),
      }),
    ),
  );
}

async function load() {
  render($("#error"));
  $("#app-body").hidden = false;
  if (!appId) return showNotFound();
  try {
    [app, documents] = await Promise.all([
      api.getApplication(appId),
      api.listDocuments({ include_archived: true }),
    ]);
    show();
    if (getParam("started") === "1") {
      toast.success(
        "Application started",
        "Follow the steps below when you're ready to apply.",
      );
      setParams({ id: app.id });
    }
    if (getParam("confirm") === "1") openConfirm();
  } catch (error) {
    if (isApiError(error) && error.code === "not_found") return showNotFound();
    if (!isApiError(error)) console.error(error); // a bug, not a network problem
    $("#app-title").textContent = "Application";
    $("#app-body").hidden = true;
    render($("#error"), errorState(error, load));
  }
}

render($("#timeline"), h("li", {}, loadingBlock()));
render($("#job-snapshot"), loadingBlock());
load();
