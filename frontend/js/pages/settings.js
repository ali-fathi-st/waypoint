/**
 * Settings (settings.html?tab=sources|notifications|account|developer)
 * - Sources: which job boards the backend collects from.
 * - Notifications: daily digest and follow-up reminder emails.
 * - Account: name, email, time zone; export or delete all data.
 * - Developer: connect this browser to your backend; where data comes from;
 *   simulate empty/slow/error states.
 */
import { initShell } from "../ui/shell.js";
import { api, apiMode, mockApi } from "../api/api.js";
import {
  connection as config,
  forgetBackendUrl,
  saveBackendUrl,
  testBackend,
} from "../connection.js";
import { describeError } from "../api/errors.js";
import { getMockScenario, setMockScenario } from "../api/mock-api.js";
import { h, render, $, $$, withBusy } from "../lib/dom.js";
import { getParam, setParams } from "../lib/url.js";
import { icon } from "../ui/icons.js";
import { toast } from "../ui/toast.js";
import { confirmAction } from "../ui/dialog.js";
import { createTagInput } from "../ui/tag-input.js";
import { errorState, loadingBlock } from "../ui/states.js";
import { saveFile } from "../ui/save-file.js";
import { formatDateTime, formatRelative } from "../lib/format.js";
import { SOURCE_LABEL } from "../lib/status.js";

initShell();

let settings = null; // last saved settings

// =============================================================== tabs

const TABS = ["sources", "notifications", "account", "developer"];
function showTab(name) {
  for (const tab of $$("[role=tab]")) {
    const active = tab.dataset.tab === name;
    tab.setAttribute("aria-selected", String(active));
    $(`#panel-${tab.dataset.tab}`).hidden = !active;
  }
  setParams({ tab: name === "sources" ? "" : name });
}
for (const tab of $$("[role=tab]"))
  tab.addEventListener("click", () => showTab(tab.dataset.tab));
showTab(TABS.includes(getParam("tab")) ? getParam("tab") : "sources");

// =============================================================== sources

const SOURCE_HELP = {
  greenhouse: {
    about:
      "Public job boards of employers that use Greenhouse. No API key needed.",
    idLabel: "Board tokens",
    placeholder: "e.g. northline",
  },
  lever: {
    about: "Public postings of employers that use Lever. No API key needed.",
    idLabel: "Company slugs",
    placeholder: "e.g. kestrel",
  },
  ashby: {
    about: "Public job boards of employers that use Ashby. No API key needed.",
    idLabel: "Board names",
    placeholder: "e.g. jobber",
  },
  rss: {
    about:
      "Employers' public RSS job feeds, such as the Government of Alberta's. Only read where the site's robots.txt allows it.",
    idLabel: "Feed addresses",
    placeholder: "e.g. https://jobpostings.alberta.ca/feeds/data/?locale=en_US",
  },
  adzuna: {
    about: "Searches many Canadian job boards through the Adzuna API.",
    idLabel: "Search terms",
    placeholder: "e.g. data engineer",
  },
};
const RUN_TEXT = {
  succeeded: ["badge--accent", "Last run succeeded"],
  partial: ["badge--warning", "Last run had failures"],
  failed: ["badge--danger", "Last run failed"],
  running: ["badge--info", "Running now"],
  never: ["", "Never run"],
};
let sourceInputs = []; // { source, enabled: <input>, ids: tag input }

function sourcesDraft() {
  return sourceInputs.map((s) => ({
    source: s.source,
    enabled: s.enabled.checked,
    identifiers: s.ids.getValues(),
  }));
}
function savedSources() {
  return settings.sources.map((s) => ({
    source: s.source,
    enabled: s.enabled,
    identifiers: s.identifiers,
  }));
}
function updateSourcesButtons() {
  const dirty =
    JSON.stringify(sourcesDraft()) !== JSON.stringify(savedSources());
  $("#sources-save").disabled = !dirty;
  $("#sources-discard").disabled = !dirty;
}

function renderSources() {
  sourceInputs = [];
  render($("#sources"));
  for (const s of settings.sources) {
    const node =
      $("#source-template").content.cloneNode(true).firstElementChild;
    const help = SOURCE_HELP[s.source];
    const q = (sel) => node.querySelector(sel);
    q("[data-name]").textContent = SOURCE_LABEL[s.source];
    q("[data-about]").textContent = help.about;

    const enabled = q("[data-enabled]");
    enabled.id = `src-${s.source}-on`;
    enabled.checked = s.enabled;
    enabled.setAttribute(
      "aria-label",
      `Collect from ${SOURCE_LABEL[s.source]}`,
    );
    const stateText = q("[data-state]");
    const setStateText = () =>
      (stateText.textContent = enabled.checked ? "On" : "Off");
    setStateText();
    enabled.addEventListener("change", () => {
      setStateText();
      updateSourcesButtons();
    });

    const idsLabel = q("[data-ids-label]");
    idsLabel.textContent = help.idLabel;
    idsLabel.htmlFor = `src-${s.source}-ids`;
    q("[data-ids-hint]").id = `src-${s.source}-hint`;
    const ids = createTagInput(q("[data-ids]"), {
      inputId: `src-${s.source}-ids`,
      values: s.identifiers,
      placeholder: help.placeholder,
      describedBy: `src-${s.source}-hint`,
      onChange: updateSourcesButtons,
    });

    if (s.source === "adzuna") {
      const creds = q("[data-credentials]");
      creds.hidden = false;
      creds.append(
        icon("key"),
        h(
          "span",
          {},
          s.credentials_configured
            ? "API keys are set on the server. "
            : "API keys aren't set. Add ADZUNA_APP_ID and ADZUNA_APP_KEY to the backend's environment. ",
          "Keys never pass through this website.",
        ),
      );
    }

    const [tone, text] = RUN_TEXT[s.last_run_status];
    const sum = s.last_run_summary;
    render(
      q("[data-run]"),
      h("span", { class: `badge ${tone}` }, text),
      s.last_run_at
        ? h(
            "span",
            { title: formatDateTime(s.last_run_at) },
            formatRelative(s.last_run_at),
          )
        : null,
      sum
        ? h(
            "span",
            {},
            `${sum.fetched} fetched, ${sum.inserted} new, ${sum.updated} updated, ${sum.skipped} unchanged${sum.failed ? `, ${sum.failed} failed` : ""}`,
          )
        : null,
    );

    sourceInputs.push({ source: s.source, enabled, ids });
    $("#sources").append(node);
  }
  updateSourcesButtons();
}

$("#sources-discard").addEventListener("click", renderSources);
$("#sources-save").addEventListener("click", async (e) => {
  await withBusy(e.currentTarget, "Saving...", async () => {
    try {
      settings = await api.updateSettings({ sources: sourcesDraft() });
      renderSources();
      toast.success(
        "Sources saved",
        "Changes apply the next time the backend collects jobs.",
      );
    } catch (err) {
      toast.error("Couldn't save sources", describeError(err));
    }
  });
  updateSourcesButtons();
});

// =============================================================== notifications

const nForm = $("#notifications-form");
const hourFormat = new Intl.DateTimeFormat("en-CA", { hour: "numeric" });
render(
  $("#n-hour"),
  Array.from({ length: 24 }, (_, hour) =>
    h(
      "option",
      { value: String(hour) },
      hourFormat.format(new Date(2026, 0, 1, hour)),
    ),
  ),
);

function notificationsDraft() {
  return {
    daily_digest: $("#n-digest").checked,
    digest_hour: Number($("#n-hour").value),
    digest_min_score: Number($("#n-min").value),
    follow_up_reminders: $("#n-follow").checked,
  };
}
function renderNotifications() {
  const n = settings.notifications;
  $("#n-digest").checked = n.daily_digest;
  $("#n-hour").value = String(n.digest_hour);
  $("#n-min").value = String(n.digest_min_score);
  $("#n-follow").checked = n.follow_up_reminders;
  updateNotifications();
}
function updateNotifications() {
  const draft = notificationsDraft();
  $("#n-hour").disabled = !draft.daily_digest;
  $("#n-min").disabled = !draft.daily_digest;
  const dirty =
    JSON.stringify(draft) !== JSON.stringify(settings.notifications);
  $("#notifications-save").disabled = !dirty;
  $("#notifications-discard").disabled = !dirty;
}
nForm.addEventListener("change", updateNotifications);
$("#notifications-discard").addEventListener("click", renderNotifications);
nForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  await withBusy($("#notifications-save"), "Saving...", async () => {
    try {
      settings = await api.updateSettings({
        notifications: notificationsDraft(),
      });
      toast.success("Notification settings saved");
    } catch (err) {
      toast.error("Couldn't save", describeError(err));
    }
  });
  renderNotifications();
});

// =============================================================== account

const aForm = $("#account-form");
function accountDraft() {
  return {
    display_name: $("#a-name").value.trim(),
    email: $("#a-email").value.trim(),
    timezone: $("#a-tz").value,
  };
}
function renderAccount() {
  $("#a-name").value = settings.account.display_name;
  $("#a-email").value = settings.account.email;
  $("#a-tz").value = settings.account.timezone;
  updateAccount();
}
function updateAccount() {
  $("#account-save").disabled =
    JSON.stringify(accountDraft()) === JSON.stringify(settings.account);
}
function fieldError(id, message) {
  const error = $(`#${id}-error`);
  error.textContent = message ?? "";
  error.hidden = !message;
  if (message) $(`#${id}`).setAttribute("aria-invalid", "true");
  else $(`#${id}`).removeAttribute("aria-invalid");
}
aForm.addEventListener("input", updateAccount);
aForm.addEventListener("change", updateAccount);
aForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const draft = accountDraft();
  const nameError = draft.display_name ? null : "Enter a display name.";
  const emailError = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(draft.email)
    ? null
    : "Enter a valid email address.";
  fieldError("a-name", nameError);
  fieldError("a-email", emailError);
  if (nameError || emailError)
    return $(nameError ? "#a-name" : "#a-email").focus();
  await withBusy($("#account-save"), "Saving...", async () => {
    try {
      settings = await api.updateSettings({ account: draft });
      toast.success("Account saved");
    } catch (err) {
      toast.error("Couldn't save", describeError(err));
    }
  });
  renderAccount();
});

$("#export").prepend(icon("download"));
$("#export").addEventListener("click", async (e) => {
  await withBusy(e.currentTarget, "Preparing...", async () => {
    try {
      const blob = await api.exportData();
      const outcome = await saveFile(
        `waypoint-export-${new Date().toISOString().slice(0, 10)}.json`,
        blob,
      );
      if (outcome === "saved") toast.success("Export downloaded");
    } catch (err) {
      toast.error("Export failed", describeError(err));
    }
  });
});

$("#delete-all").prepend(icon("trash"));
$("#delete-all").addEventListener("click", async () => {
  const ok = await confirmAction({
    title: "Delete all data?",
    message:
      "Every job, application, document and your profile will be permanently removed. Download an export first if you might need it.",
    confirmLabel: "Delete everything",
    danger: true,
    requireText: "DELETE",
  });
  if (!ok) return;
  try {
    await api.deleteAllData();
    toast.success("All data deleted");
    load();
  } catch (err) {
    toast.error("Couldn't delete data", describeError(err));
  }
});

// =============================================================== developer

// ---- connect this browser to your backend (saved in this browser only)
const connectedHere = config.source === "browser";

function backendError(message) {
  const error = $("#backend-url-error");
  error.textContent = message ?? "";
  error.hidden = !message;
  $("#backend-url").setAttribute("aria-invalid", message ? "true" : "false");
}

function renderBackend() {
  $("#backend-url").value = connectedHere
    ? config.apiBaseUrl
    : "http://localhost:8000";
  $("#backend-forget").hidden = !connectedHere;
  $("#backend-connect").textContent = connectedHere
    ? "Save address"
    : "Connect";
  $("#backend-status").textContent = connectedHere
    ? `This browser is connected to ${config.apiBaseUrl}.`
    : apiMode === "mock"
      ? "This browser is using sample data."
      : `This site is set up (in js/config.js) to use ${config.apiBaseUrl}.`;
}

$("#backend-test").addEventListener("click", async (e) => {
  backendError(null);
  await withBusy(e.currentTarget, "Testing...", async () => {
    try {
      await testBackend($("#backend-url").value);
      toast.success("Your backend answered", "Choose Connect to use it.");
    } catch (err) {
      backendError(err.message);
    }
  });
});

$("#backend-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  backendError(null);
  await withBusy($("#backend-connect"), "Connecting...", async () => {
    try {
      await testBackend($("#backend-url").value);
      saveBackendUrl($("#backend-url").value);
      toast.success("Connected", "Reloading with your real data...");
      setTimeout(() => window.location.reload(), 600);
    } catch (err) {
      backendError(err.message);
    }
  });
});

$("#backend-forget").addEventListener("click", () => {
  forgetBackendUrl();
  toast.success("Disconnected", "Reloading with sample data...");
  setTimeout(() => window.location.reload(), 600);
});

renderBackend();

function renderDataSource() {
  const where =
    apiMode === "mock"
      ? "Built-in sample data (the mock API). Nothing is sent anywhere."
      : apiMode === "http"
        ? `Your backend at ${config.apiBaseUrl}${connectedHere ? " (saved in this browser)" : " (set in js/config.js)"}.`
        : `Your backend at ${config.apiBaseUrl} for ${config.liveOperations.join(", ")}; sample data for everything else.`;
  render(
    $("#data-source"),
    h("p", {}, h("strong", { class: "title-link" }, "Now using: "), where),
    h(
      "p",
      {},
      "To connect a backend for every visitor instead, edit ",
      h("code", {}, "frontend/js/config.js"),
      ": set ",
      h("code", {}, 'apiMode: "http"'),
      " and ",
      h("code", {}, "apiBaseUrl"),
      ". To connect one endpoint at a time, use ",
      h("code", {}, 'apiMode: "hybrid"'),
      " and list the working ones in ",
      h("code", {}, "liveOperations"),
      ". Details: docs/07-connecting-the-backend.md.",
    ),
  );
}

if (mockApi) {
  const current = getMockScenario();
  for (const radio of $$('input[name="scenario"]')) {
    radio.checked = radio.value === current;
    radio.addEventListener("change", () => {
      setMockScenario(radio.value);
      toast.success("Scenario changed", "Reloading so every page uses it...");
      setTimeout(() => window.location.reload(), 600);
    });
  }
  $("#reset-sample").prepend(icon("restore"));
  $("#reset-sample").addEventListener("click", () => {
    mockApi.reset();
    toast.success("Sample data reset");
    load();
  });
} else {
  $("#simulate").hidden = true;
}

// =============================================================== load

async function load() {
  render($("#error"));
  render($("#sources"), loadingBlock());
  try {
    settings = await api.getSettings();
    renderSources();
    renderNotifications();
    renderAccount();
  } catch (error) {
    render($("#sources"));
    render($("#error"), errorState(error, load));
  }
}

renderDataSource();
load();
