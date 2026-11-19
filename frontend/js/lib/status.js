/**
 * Application and job status rules, plus display labels.
 * The backend should enforce the same transitions; the UI only uses them to
 * decide which options to show.
 */
export const APPLICATION_STATUSES = [
  "saved",
  "preparing",
  "ready_for_review",
  "applied",
  "interview",
  "offer",
  "rejected",
  "withdrawn",
];

export const APPLICATION_STATUS_LABEL = {
  saved: "Saved",
  preparing: "Preparing",
  ready_for_review: "Ready for review",
  applied: "Applied",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

/**
 * Allowed moves by PATCH. "applied" is intentionally absent: the only way in
 * is the confirm-submission step (see CONFIRMABLE_STATUSES).
 */
export const STATUS_TRANSITIONS = {
  saved: ["preparing", "withdrawn"],
  preparing: ["saved", "ready_for_review", "withdrawn"],
  ready_for_review: ["preparing", "withdrawn"],
  applied: ["interview", "offer", "rejected", "withdrawn"],
  interview: ["offer", "rejected", "withdrawn"],
  offer: ["rejected", "withdrawn"],
  rejected: [],
  withdrawn: [],
};

/** Statuses from which you can confirm that you submitted the application. */
export const CONFIRMABLE_STATUSES = ["saved", "preparing", "ready_for_review"];

/** Statuses that count as "submitted" for metrics. */
export const SUBMITTED_STATUSES = ["applied", "interview", "offer", "rejected"];

/** Statuses where a follow-up reminder still makes sense. */
export const FOLLOW_UP_STATUSES = ["applied", "interview"];

export const DEFAULT_FOLLOW_UP_DAYS = 14;

export function canTransition(from, to) {
  if (to === "applied") return false;
  return STATUS_TRANSITIONS[from].includes(to);
}

export function canConfirmSubmission(status) {
  return CONFIRMABLE_STATUSES.includes(status);
}

export function isTerminal(status) {
  return STATUS_TRANSITIONS[status].length === 0;
}

export const JOB_REVIEW_LABEL = {
  new: "New",
  shortlisted: "Shortlisted",
  dismissed: "Dismissed",
};

export const SOURCE_LABEL = {
  greenhouse: "Greenhouse",
  lever: "Lever",
  ashby: "Ashby",
  rss: "Employer feeds",
  adzuna: "Adzuna",
  manual: "Added manually",
};

export const WORK_ARRANGEMENT_LABEL = {
  onsite: "On-site",
  hybrid: "Hybrid",
  remote: "Remote",
  unknown: "Not stated",
};

export const EMPLOYMENT_TYPE_LABEL = {
  full_time: "Full-time",
  part_time: "Part-time",
  contract: "Contract",
  temporary: "Temporary",
  internship: "Internship",
  unknown: "Not stated",
};
