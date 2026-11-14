/**
 * Documents (documents.html): résumé versions and cover-letter drafts.
 * Upload a version, review a draft and mark it ready, archive old ones.
 */
import { initShell } from "../ui/shell.js";
import { api, apiMode } from "../api/api.js";
import { describeError } from "../api/errors.js";
import { h, render, $, $$, withBusy } from "../lib/dom.js";
import { icon } from "../ui/icons.js";
import { toast } from "../ui/toast.js";
import { setupDialog } from "../ui/dialog.js";
import { documentBadge } from "../ui/badges.js";
import { emptyState, errorState, loadingRows } from "../ui/states.js";
import { formatBytes, formatDate } from "../lib/format.js";

initShell();
for (const close of document.querySelectorAll(".dialog__close"))
  close.append(icon("close"));
$("#upload-open").prepend(icon("upload"));

const TYPE_LABEL = { resume: "Résumé", cover_letter: "Cover letter" };
const MAX_BYTES = 5 * 1024 * 1024;
const ALLOWED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];
const state = { type: "", showArchived: false };

// ---- List ----
function rowActions(doc) {
  const set = async (button, status, message) => {
    await withBusy(button, null, async () => {
      try {
        await api.updateDocument(doc.id, { status });
        toast.success(message);
        load();
      } catch (e) {
        toast.error("Couldn't update the document", describeError(e));
      }
    });
  };
  const buttons = [];
  if (doc.status === "draft") {
    const ready = h(
      "button",
      {
        type: "button",
        class: "btn btn--sm",
        "aria-label": `Mark ${doc.title} as reviewed and ready`,
      },
      icon("check-circle"),
      "Mark ready",
    );
    ready.addEventListener("click", () =>
      set(ready, "ready", "Marked as ready"),
    );
    buttons.push(ready);
  }
  const archived = doc.status === "archived";
  const toggle = h(
    "button",
    {
      type: "button",
      class: "btn btn--ghost btn--sm",
      "aria-label": `${archived ? "Restore" : "Archive"} ${doc.title}`,
    },
    icon(archived ? "restore" : "archive"),
    archived ? "Restore" : "Archive",
  );
  toggle.addEventListener("click", () =>
    set(
      toggle,
      archived ? "ready" : "archived",
      archived ? "Restored" : "Archived",
    ),
  );
  buttons.push(toggle);
  return h("div", { class: "row row--end" }, buttons);
}

function renderList(docs) {
  if (!docs.length) {
    render(
      $("#results"),
      emptyState({
        iconName: "documents",
        title:
          state.type === "cover_letter"
            ? "No cover letters yet"
            : "No documents yet",
        description:
          "Upload your current résumé so you can link it to applications.",
      }),
    );
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
            [
              "Document",
              "Version",
              "Source",
              "Status",
              "Linked job",
              "Updated",
            ].map((t) => h("th", { scope: "col" }, t)),
            h(
              "th",
              { scope: "col", class: "actions" },
              h("span", { class: "sr-only" }, "Actions"),
            ),
          ),
        ),
        h(
          "tbody",
          {},
          docs.map((d) =>
            h(
              "tr",
              { class: d.status === "archived" ? "muted" : null },
              h(
                "td",
                { class: "stack-main" },
                h("span", { class: "title-link block" }, d.title),
                h(
                  "span",
                  { class: "small muted" },
                  TYPE_LABEL[d.document_type],
                  d.file_name
                    ? `, ${d.file_name} (${formatBytes(d.size_bytes)})`
                    : "",
                ),
              ),
              h(
                "td",
                { class: "stack-full ink-2" },
                h("span", { class: "stack-only" }, "Version "),
                `v${d.version}`,
              ),
              h(
                "td",
                { class: "stack-hide ink-2" },
                d.origin === "generated" ? "AI draft" : "Uploaded",
              ),
              h("td", { class: "stack-full" }, documentBadge(d.status)),
              h(
                "td",
                { class: "stack-full" },
                d.related_job_id
                  ? h(
                      "a",
                      {
                        href: `job.html?id=${encodeURIComponent(d.related_job_id)}`,
                      },
                      d.related_job_title ?? "View job",
                    )
                  : h("span", { class: "muted" }, "General"),
              ),
              h(
                "td",
                { class: "stack-hide ink-2 nowrap" },
                formatDate(d.updated_at),
              ),
              h("td", { class: "actions stack-full" }, rowActions(d)),
            ),
          ),
        ),
      ),
    ),
  );
}

async function load() {
  render($("#error"));
  if (!$("#results").children.length) render($("#results"), loadingRows(5));
  try {
    renderList(
      await api.listDocuments({
        document_type: state.type || undefined,
        include_archived: state.showArchived,
      }),
    );
  } catch (error) {
    render($("#results"));
    render($("#error"), errorState(error, load));
  }
}

for (const tab of $$("[role=tab]")) {
  tab.addEventListener("click", () => {
    state.type = tab.dataset.type;
    for (const t of $$("[role=tab]"))
      t.setAttribute("aria-selected", String(t === tab));
    load();
  });
}
$("#show-archived").addEventListener("change", (e) => {
  state.showArchived = e.target.checked;
  load();
});

// ---- Upload ----
const dialog = setupDialog($("#upload-dialog"));
if (apiMode !== "http") {
  $("#upload-desc").textContent +=
    " With sample data, only the file name and size are kept; the file stays on your computer.";
}

function fieldError(id, message) {
  const el = $(`#${id}-error`);
  el.textContent = message ?? "";
  el.hidden = !message;
  const input = document.getElementById(id);
  if (message) input.setAttribute("aria-invalid", "true");
  else input.removeAttribute("aria-invalid");
}

$("#upload-open").addEventListener("click", async () => {
  $("#upload-form").reset();
  fieldError("u-title", null);
  fieldError("u-file", null);
  dialog.showModal();
  // Offer shortlisted jobs to link the version to.
  try {
    const { items } = await api.listJobs({
      review_status: "shortlisted",
      limit: 100,
      sort: "newest",
    });
    render(
      $("#u-job"),
      h("option", { value: "" }, "Not linked"),
      items.map((j) =>
        h("option", { value: j.id }, `${j.title}, ${j.company.name}`),
      ),
    );
  } catch {
    /* linking is optional; keep "Not linked" */
  }
});

$("#upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = $("#u-title").value.trim();
  const file = $("#u-file").files[0];
  const titleError = title ? null : "Give this version a name.";
  const fileError = !file
    ? "Choose a file."
    : !ALLOWED_TYPES.includes(file.type)
      ? "Upload a PDF or Word (.docx) file."
      : file.size > MAX_BYTES
        ? "The file must be 5 MB or smaller."
        : null;
  fieldError("u-title", titleError);
  fieldError("u-file", fileError);
  if (titleError || fileError) {
    document.getElementById(titleError ? "u-title" : "u-file").focus();
    return;
  }

  await withBusy($("#upload-submit"), "Uploading...", async () => {
    try {
      const doc = await api.uploadDocument({
        document_type: $("#u-type").value,
        title,
        related_job_id: $("#u-job").value || null,
        file,
      });
      dialog.close();
      toast.success(
        `Uploaded ${TYPE_LABEL[doc.document_type].toLowerCase()} v${doc.version}`,
      );
      load();
    } catch (err) {
      toast.error("Upload failed", describeError(err));
    }
  });
});

load();
