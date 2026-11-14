/**
 * A list of short values shown as removable chips: target titles,
 * locations, source identifiers. Enter or comma adds; Backspace on an empty
 * box removes the last chip.
 *
 *   const titles = createTagInput(document.getElementById("titles"), {
 *     inputId: "titles-input", values: ["Data Engineer"], placeholder: "Add a title",
 *   });
 *   titles.getValues();
 */
import { h, render } from "../lib/dom.js";
import { icon } from "./icons.js";

export function createTagInput(
  container,
  {
    inputId,
    values = [],
    placeholder = "",
    onChange = () => {},
    describedBy,
  } = {},
) {
  let items = [...values];
  container.classList.add("tags");

  const input = h("input", {
    id: inputId,
    type: "text",
    placeholder,
    "aria-describedby": describedBy ?? null,
  });

  function add(raw) {
    const value = raw.trim().replace(/,$/, "").trim();
    input.value = "";
    if (!value || items.some((x) => x.toLowerCase() === value.toLowerCase()))
      return;
    items = [...items, value];
    draw();
    onChange(items);
  }

  function remove(value) {
    items = items.filter((x) => x !== value);
    draw();
    onChange(items);
    input.focus();
  }

  function draw() {
    render(
      container,
      items.map((value) =>
        h(
          "span",
          { class: "tag" },
          value,
          h(
            "button",
            {
              type: "button",
              "aria-label": `Remove ${value}`,
              onclick: () => remove(value),
            },
            icon("close"),
          ),
        ),
      ),
      input,
    );
    input.placeholder = items.length ? "" : placeholder;
  }

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      add(input.value);
    } else if (e.key === "Backspace" && !input.value && items.length) {
      remove(items[items.length - 1]);
    }
  });
  input.addEventListener("input", () => {
    if (input.value.endsWith(",")) add(input.value);
  });
  input.addEventListener("blur", () => add(input.value));

  draw();
  return {
    getValues: () => [...items],
    setValues: (next) => {
      items = [...next];
      draw();
    },
    setInvalid: (invalid) =>
      invalid
        ? container.setAttribute("aria-invalid", "true")
        : container.removeAttribute("aria-invalid"),
  };
}
