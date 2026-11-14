/**
 * Builds the navigation around every page: the sidebar on desktop and the
 * top bar with a slide-out menu on phones. Each HTML page has an empty
 * <div id="shell"> and <body data-page="jobs"> to mark the current page.
 */
import { h } from "../lib/dom.js";
import { icon } from "./icons.js";
import { apiMode } from "../api/api.js";
import { config } from "../config.js";
import { getMockScenario } from "../api/mock-api.js";

export const NAV_ITEMS = [
  {
    page: "dashboard",
    href: "index.html",
    label: "Dashboard",
    icon: "dashboard",
  },
  { page: "jobs", href: "jobs.html", label: "Jobs", icon: "jobs" },
  {
    page: "applications",
    href: "applications.html",
    label: "Applications",
    icon: "applications",
  },
  {
    page: "documents",
    href: "documents.html",
    label: "Documents",
    icon: "documents",
  },
  { page: "profile", href: "profile.html", label: "Profile", icon: "profile" },
  {
    page: "settings",
    href: "settings.html",
    label: "Settings",
    icon: "settings",
  },
];

const SCENARIO_TEXT = {
  empty: "Showing empty data",
  slow: "Slow responses on",
  error: "Every request fails",
};

function brand() {
  return h(
    "a",
    { href: "index.html", class: "brand" },
    h("img", { src: "assets/logo.svg", alt: "" }),
    "Waypoint",
  );
}

function navList(current) {
  return h(
    "ul",
    { class: "nav-list" },
    NAV_ITEMS.map((item) =>
      h(
        "li",
        {},
        h(
          "a",
          {
            href: item.href,
            class: "nav-link",
            "aria-current": item.page === current ? "page" : null,
          },
          icon(item.icon),
          item.label,
        ),
      ),
    ),
  );
}

/** Small note saying where the data comes from. */
function dataNote() {
  if (apiMode === "http") {
    return h(
      "p",
      { class: "data-note" },
      icon("database"),
      h("span", {}, `Connected to ${config.apiBaseUrl}`),
    );
  }
  const scenario = getMockScenario();
  return h(
    "a",
    { href: "settings.html?tab=developer", class: "data-note" },
    icon("sample"),
    h(
      "span",
      {},
      apiMode === "hybrid"
        ? `${config.liveOperations.length} ${config.liveOperations.length === 1 ? "operation" : "operations"} live from ${config.apiBaseUrl}, the rest sample data`
        : "Sample data, not connected to a backend",
      SCENARIO_TEXT[scenario] ? h("strong", {}, SCENARIO_TEXT[scenario]) : null,
    ),
  );
}

export function initShell() {
  const host = document.getElementById("shell");
  if (!host) return;
  const current = document.body.dataset.page;

  const drawer = h(
    "dialog",
    { class: "drawer", "aria-label": "Menu" },
    h(
      "div",
      { class: "drawer__head" },
      brand(),
      h(
        "button",
        {
          class: "btn btn--ghost btn--icon",
          type: "button",
          "aria-label": "Close menu",
          onclick: () => drawer.close(),
        },
        icon("close"),
      ),
    ),
    h("nav", { class: "sidebar__nav", "aria-label": "Main" }, navList(current)),
    h("div", { class: "sidebar__footer" }, dataNote()),
  );
  // Clicking the dimmed area outside the menu closes it.
  drawer.addEventListener("click", (e) => {
    if (e.target === drawer) drawer.close();
  });

  host.replaceWith(
    h(
      "aside",
      { class: "sidebar" },
      h("div", { class: "sidebar__brand" }, brand()),
      h(
        "nav",
        { class: "sidebar__nav", "aria-label": "Main" },
        navList(current),
      ),
      h("div", { class: "sidebar__footer" }, dataNote()),
    ),
    h(
      "div",
      { class: "topbar" },
      h(
        "button",
        {
          class: "btn btn--ghost btn--icon",
          type: "button",
          "aria-label": "Open menu",
          onclick: () => drawer.showModal(),
        },
        icon("menu"),
      ),
      brand(),
    ),
    drawer,
  );
}
