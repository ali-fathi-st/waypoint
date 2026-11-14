/**
 * The "Move to..." dropdown for an application. It lists only the statuses
 * the application can move to next. "Applied" is never a direct option:
 * "Record as applied..." opens the confirmation step instead, because
 * Waypoint must never claim an application was sent without the user
 * confirming they sent it.
 */
import { h } from "../lib/dom.js";
import { api } from "../api/api.js";
import { describeError } from "../api/errors.js";
import { toast } from "./toast.js";
import { confirmAction } from "./dialog.js";
import {
  APPLICATION_STATUS_LABEL,
  STATUS_TRANSITIONS,
  canConfirmSubmission,
} from "../lib/status.js";

const CLOSING = ["withdrawn", "rejected"];

/**
 * onChange(updatedApp) runs after a successful change.
 * onRecordApplied() runs for "Record as applied..."; by default it opens the
 * application page with the confirmation dialog.
 */
export function statusSelect(
  app,
  { onChange = () => {}, onRecordApplied, small = false } = {},
) {
  const targets = STATUS_TRANSITIONS[app.status];
  const confirmable = canConfirmSubmission(app.status);
  if (!targets.length && !confirmable) return null;

  const select = h(
    "select",
    { class: "select", "aria-label": `Change status of ${app.job.title}` },
    h("option", { value: "", selected: true, disabled: true }, "Move to..."),
    confirmable
      ? h("option", { value: "__applied" }, "Record as applied...")
      : null,
    targets.map((status) =>
      h("option", { value: status }, APPLICATION_STATUS_LABEL[status]),
    ),
  );
  if (small) select.classList.add("select--sm");

  select.addEventListener("change", async () => {
    const to = select.value;
    select.value = "";
    if (to === "__applied") {
      if (onRecordApplied) onRecordApplied();
      else
        window.location.href = `application.html?id=${encodeURIComponent(app.id)}&confirm=1`;
      return;
    }
    if (CLOSING.includes(to)) {
      const label = APPLICATION_STATUS_LABEL[to].toLowerCase();
      const ok = await confirmAction({
        title: `Mark as ${label}?`,
        message: `${app.job.title} at ${app.job.company_name} will be closed and its follow-up reminder cleared. A closed application can't be reopened.`,
        confirmLabel: `Mark as ${label}`,
        danger: true,
      });
      if (!ok) return;
    }
    select.disabled = true;
    try {
      const updated = await api.updateApplication(app.id, { status: to });
      toast.success(`Moved to ${APPLICATION_STATUS_LABEL[to].toLowerCase()}`);
      onChange(updated);
    } catch (e) {
      toast.error("Couldn't change the status", describeError(e));
    } finally {
      select.disabled = false;
    }
  });
  return select;
}
