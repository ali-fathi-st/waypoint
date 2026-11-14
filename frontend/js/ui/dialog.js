/**
 * Dialogs use the browser's built-in <dialog> element: it traps keyboard
 * focus, closes on Esc, and dims the page, with no extra code.
 *
 * - Dialogs with forms (upload, interview, record as applied) are written in
 *   the page's HTML. setupDialog() wires their close buttons.
 * - confirmAction() builds a quick "Are you sure?" dialog on the fly.
 */
import { h } from "../lib/dom.js";
import { icon } from "./icons.js";

/** Make every [data-close] button inside the dialog close it. */
export function setupDialog(dialog) {
  for (const button of dialog.querySelectorAll("[data-close]")) {
    button.addEventListener("click", () => dialog.close());
  }
  return dialog;
}

/** A close (X) button for a dialog header. */
export function closeButton(dialog) {
  return h(
    "button",
    {
      type: "button",
      class: "btn btn--ghost btn--icon dialog__close",
      "aria-label": "Close",
      onclick: () => dialog.close(),
    },
    icon("close"),
  );
}

/**
 * Ask before doing something important. Resolves true if confirmed.
 *   if (await confirmAction({ title: "Withdraw?", message: "...", confirmLabel: "Withdraw", danger: true })) ...
 * requireText: the user must type this word first (for irreversible actions).
 */
export function confirmAction({
  title,
  message,
  confirmLabel,
  danger = false,
  requireText = null,
}) {
  return new Promise((resolve) => {
    const confirmButton = h(
      "button",
      {
        type: "submit",
        class: `btn ${danger ? "btn--danger" : "btn--primary"}`,
        disabled: Boolean(requireText),
      },
      confirmLabel,
    );
    const typed = requireText
      ? h("input", {
          class: "input",
          id: "confirm-text",
          autocomplete: "off",
          oninput: (e) => {
            confirmButton.disabled = e.target.value !== requireText;
          },
        })
      : null;

    const dialog = h("dialog", {
      class: "dialog dialog--sm",
      "aria-labelledby": "confirm-title",
    });
    const form = h(
      "form",
      { method: "dialog" },
      h(
        "div",
        { class: "dialog__head" },
        h("h2", { id: "confirm-title" }, title),
        closeButton(dialog),
      ),
      h(
        "div",
        { class: "dialog__body" },
        h("p", {}, message),
        typed
          ? h(
              "div",
              { class: "field" },
              h(
                "label",
                { for: "confirm-text" },
                `Type ${requireText} to confirm`,
              ),
              typed,
            )
          : null,
      ),
      h(
        "div",
        { class: "dialog__foot" },
        h(
          "button",
          { type: "button", class: "btn", onclick: () => dialog.close() },
          "Cancel",
        ),
        confirmButton,
      ),
    );
    dialog.append(form);

    let confirmed = false;
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      confirmed = true;
      dialog.close();
    });
    dialog.addEventListener("close", () => {
      dialog.remove();
      resolve(confirmed);
    });
    document.body.append(dialog);
    dialog.showModal();
  });
}
