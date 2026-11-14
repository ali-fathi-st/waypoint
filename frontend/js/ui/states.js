/**
 * Loading, empty and error states, so no list is ever just blank.
 */
import { h } from "../lib/dom.js";
import { icon } from "./icons.js";
import { describeError } from "../api/errors.js";

/** Grey placeholder rows while data loads. */
export function loadingRows(count = 6) {
  return h(
    "div",
    { class: "skeleton-rows", role: "status", "aria-label": "Loading" },
    Array.from({ length: count }, () =>
      h(
        "div",
        { class: "skeleton-row" },
        h("div", { class: "skeleton skeleton--score" }),
        h(
          "div",
          { class: "skeleton-lines" },
          h("div", { class: "skeleton skeleton--line skeleton--w40" }),
          h("div", { class: "skeleton skeleton--line skeleton--w25" }),
        ),
      ),
    ),
  );
}

/** A few lines of placeholder text. */
export function loadingBlock() {
  return h(
    "div",
    {
      class: "skeleton-lines skeleton-lines--block",
      role: "status",
      "aria-label": "Loading",
    },
    h("div", { class: "skeleton skeleton--title" }),
    h("div", { class: "skeleton skeleton--line skeleton--w65" }),
    h("div", { class: "skeleton skeleton--line skeleton--w50" }),
  );
}

/** Nothing to show: say why, and what to do next. */
export function emptyState({ iconName = "inbox", title, description, action }) {
  return h(
    "div",
    { class: "empty" },
    icon(iconName),
    h("strong", {}, title),
    description ? h("p", {}, description) : null,
    action ?? null,
  );
}

/** Something failed: say what, and offer a retry. */
export function errorState(error, onRetry, title = "Couldn't load this") {
  if (!(error && error.name === "ApiError")) console.error(error); // a bug, not a network problem
  return h(
    "div",
    { class: "alert", role: "alert" },
    icon("error"),
    h(
      "div",
      { class: "alert__text" },
      h("strong", {}, title),
      h("span", {}, describeError(error)),
    ),
    onRetry
      ? h(
          "button",
          { type: "button", class: "btn btn--sm", onclick: onRetry },
          icon("refresh"),
          "Try again",
        )
      : null,
  );
}
