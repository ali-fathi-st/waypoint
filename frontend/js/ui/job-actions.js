/**
 * Shortlist / Dismiss / Restore buttons for a job. Used on the dashboard,
 * the jobs list and the job page. onChange(updatedJob) runs after a change
 * so the page can refresh what it shows.
 */
import { h } from "../lib/dom.js";
import { icon } from "./icons.js";
import { toast } from "./toast.js";
import { api } from "../api/api.js";
import { describeError } from "../api/errors.js";

async function setStatus(job, status, message, onChange, buttons) {
  buttons.forEach((b) => (b.disabled = true));
  try {
    const updated = await api.updateJobStatus(job.id, status);
    toast.success(message);
    onChange(updated);
  } catch (e) {
    toast.error("Couldn't update the job", describeError(e));
    buttons.forEach((b) => (b.disabled = false));
  }
}

/** compact: icon-only buttons for list rows. */
export function jobActions(job, { compact = false, onChange = () => {} } = {}) {
  const buttons = [];
  const shortlisted = job.review_status === "shortlisted";

  if (job.review_status === "dismissed") {
    const restore = h(
      "button",
      {
        type: "button",
        class: `btn${compact ? " btn--sm btn--ghost" : ""}`,
        onclick: () => setStatus(job, "new", "Job restored", onChange, buttons),
      },
      icon("restore"),
      "Restore",
    );
    buttons.push(restore);
    return h("div", { class: "row row--end" }, restore);
  }

  const toggle = compact
    ? h(
        "button",
        {
          type: "button",
          class: "btn btn--ghost btn--icon",
          "aria-pressed": String(shortlisted),
          "aria-label": shortlisted
            ? `Remove ${job.title} from shortlist`
            : `Shortlist ${job.title}`,
          title: shortlisted ? "Remove from shortlist" : "Shortlist",
        },
        icon("star"),
      )
    : h(
        "button",
        { type: "button", class: "btn", "aria-pressed": String(shortlisted) },
        icon("star"),
        shortlisted ? "Shortlisted" : "Shortlist",
      );
  toggle.addEventListener("click", () =>
    setStatus(
      job,
      shortlisted ? "new" : "shortlisted",
      shortlisted ? "Removed from shortlist" : "Shortlisted",
      onChange,
      buttons,
    ),
  );

  const dismiss = compact
    ? h(
        "button",
        {
          type: "button",
          class: "btn btn--ghost btn--icon",
          "aria-label": `Dismiss ${job.title}`,
          title: "Dismiss",
        },
        icon("dismiss"),
      )
    : h(
        "button",
        { type: "button", class: "btn btn--ghost" },
        icon("dismiss"),
        "Dismiss",
      );
  dismiss.addEventListener("click", () =>
    setStatus(job, "dismissed", "Job dismissed", onChange, buttons),
  );

  buttons.push(toggle, dismiss);
  return h("div", { class: "row row--end" }, toggle, dismiss);
}
