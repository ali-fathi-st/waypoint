/**
 * "Follow up Nov 24", "Follow up today", "Follow-up overdue by 2 days".
 * Only shown for applications that still need a follow-up (applied or
 * interviewing).
 */
import { h } from "../lib/dom.js";
import { icon } from "./icons.js";
import { daysUntil, formatShortDate } from "../lib/format.js";
import { FOLLOW_UP_STATUSES } from "../lib/status.js";

/** { days, due } or null when no follow-up applies. */
export function followUpState(app) {
  if (!app.follow_up_at || !FOLLOW_UP_STATUSES.includes(app.status))
    return null;
  const days = daysUntil(app.follow_up_at);
  return { days, due: days <= 0 };
}

export function followUpLabel(app) {
  const state = followUpState(app);
  if (!state) return null;
  const { days } = state;
  const text =
    days < 0
      ? `Follow-up overdue by ${-days} day${days === -1 ? "" : "s"}`
      : days === 0
        ? "Follow up today"
        : `Follow up ${formatShortDate(app.follow_up_at)}`;
  return h(
    "span",
    { class: `follow-up${days <= 0 ? " follow-up--due" : ""}` },
    icon(days <= 0 ? "warning" : "calendar"),
    text,
  );
}
