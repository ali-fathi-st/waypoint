/**
 * Short confirmations ("Shortlisted", "Notes saved") at the top of the page.
 * They disappear after a few seconds and are announced to screen readers.
 */
import { h } from "../lib/dom.js";
import { icon } from "./icons.js";

function region() {
  let el = document.getElementById("toasts");
  if (!el) {
    el = h("div", { id: "toasts", class: "toasts", "aria-live": "polite" });
    document.body.append(el);
  }
  return el;
}

function show(kind, title, description) {
  const toast = h(
    "div",
    {
      class: `toast${kind === "error" ? " toast--error" : ""}`,
      role: kind === "error" ? "alert" : "status",
    },
    icon(kind === "error" ? "error" : "check-circle"),
    h(
      "div",
      {},
      h("p", {}, title),
      description ? h("p", {}, description) : null,
    ),
  );
  region().append(toast);
  setTimeout(() => toast.remove(), kind === "error" ? 7000 : 4000);
}

export const toast = {
  success: (title, description) => show("success", title, description),
  error: (title, description) => show("error", title, description),
};
