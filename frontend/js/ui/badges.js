/**
 * Status badges. Each has an icon AND a word, so meaning never depends on
 * color alone.
 */
import { h } from "../lib/dom.js";
import { icon } from "./icons.js";
import { APPLICATION_STATUS_LABEL, JOB_REVIEW_LABEL } from "../lib/status.js";

const APPLICATION_STYLE = {
  saved: ["", "bookmark"],
  preparing: ["", "pencil"],
  ready_for_review: ["badge--warning", "eye"],
  applied: ["badge--info", "send"],
  interview: ["badge--accent", "calendar"],
  offer: ["badge--accent", "trophy"],
  rejected: ["badge--danger", "rejected"],
  withdrawn: ["badge--outline", "withdrawn"],
};

export function applicationBadge(status) {
  const [tone, iconName] = APPLICATION_STYLE[status];
  return h(
    "span",
    { class: `badge ${tone}` },
    icon(iconName),
    APPLICATION_STATUS_LABEL[status],
  );
}

export function applicationIconName(status) {
  return APPLICATION_STYLE[status][1];
}

const JOB_STYLE = {
  new: ["badge--info", "dot"],
  shortlisted: ["badge--accent", "star"],
  dismissed: ["", "dismiss"],
};

export function jobBadge(status) {
  const [tone, iconName] = JOB_STYLE[status];
  return h(
    "span",
    { class: `badge ${tone}` },
    icon(iconName),
    JOB_REVIEW_LABEL[status],
  );
}

const DOCUMENT_STYLE = {
  draft: ["badge--warning", "Draft, needs review"],
  ready: ["badge--accent", "Ready"],
  archived: ["badge--outline", "Archived"],
};

export function documentBadge(status) {
  const [tone, label] = DOCUMENT_STYLE[status];
  return h("span", { class: `badge ${tone}` }, label);
}
