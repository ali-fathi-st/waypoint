/**
 * Tiny DOM helpers. The whole site builds HTML with h(), which always
 * inserts text as text (never as HTML). That matters because job
 * descriptions come from other websites and must never run as code.
 */

/**
 * Create an element.
 *   h("a", { href: "jobs.html", class: "btn" }, "Browse jobs")
 *   h("button", { onclick: () => save() }, icon("check"), "Save")
 * Props: class, text, dataset, on<event> handlers, booleans (true = present),
 * anything else becomes an attribute. null/false/undefined are skipped.
 * Children: strings, numbers, elements, arrays (nested), null (skipped).
 */
export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props ?? {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "text") el.textContent = value;
    else if (key === "dataset") Object.assign(el.dataset, value);
    else if (key.startsWith("on") && typeof value === "function") {
      el.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (value === true) el.setAttribute(key, "");
    else el.setAttribute(key, String(value));
  }
  append(el, children);
  return el;
}

/** Append children (same rules as h). */
export function append(parent, children) {
  for (const child of [children].flat(Infinity)) {
    if (
      child === null ||
      child === undefined ||
      child === false ||
      child === ""
    )
      continue;
    parent.append(child instanceof Node ? child : String(child));
  }
  return parent;
}

/** Replace everything inside an element. */
export function render(parent, ...children) {
  parent.replaceChildren();
  return append(parent, children);
}

/** document.querySelector that throws a clear error if the element is missing. */
export function $(selector, root = document) {
  const el = root.querySelector(selector);
  if (!el) throw new Error(`Element not found: ${selector}`);
  return el;
}

/** All matches as an array. */
export function $$(selector, root = document) {
  return [...root.querySelectorAll(selector)];
}

/** Run fn after the user stops typing for `ms`. */
export function debounce(fn, ms = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

/** Disable a button while an async action runs, showing `busyText` meanwhile. */
export async function withBusy(button, busyText, action) {
  const original = [...button.childNodes];
  button.disabled = true;
  if (busyText) button.textContent = busyText;
  try {
    return await action();
  } finally {
    button.disabled = false;
    if (busyText) button.replaceChildren(...original);
  }
}
