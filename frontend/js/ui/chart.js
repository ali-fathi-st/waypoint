/**
 * A small bar chart drawn with plain SVG (no chart library).
 * One series, so no legend: the panel title names it. Hover or focus a bar
 * to read its value; a hidden table gives screen readers the same numbers.
 *
 *   barChart(container, [{ label: "Nov 3", value: 2 }, ...], { unit: "jobs found" })
 */
import { h, render } from "../lib/dom.js";

const SVG = "http://www.w3.org/2000/svg";

function svg(tag, attrs = {}, text) {
  const el = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
  if (text !== undefined) el.textContent = text;
  return el;
}

export function barChart(container, data, { unit = "" } = {}) {
  const width = 600;
  const height = 200;
  const pad = { top: 8, right: 4, bottom: 24, left: 28 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const max = Math.max(1, ...data.map((d) => d.value));
  const ticks = [...new Set([0, Math.ceil(max / 2), max])];
  const slot = plotW / data.length;
  const barW = Math.min(24, slot * 0.7);
  const y = (v) => pad.top + plotH - (v / max) * plotH;

  const chart = svg("svg", {
    viewBox: `0 0 ${width} ${height}`,
    role: "img",
    "aria-label": `Bar chart of ${unit} per day`,
  });
  for (const t of ticks) {
    chart.append(
      svg("line", {
        class: "grid-line",
        x1: pad.left,
        x2: width - pad.right,
        y1: y(t),
        y2: y(t),
      }),
    );
    chart.append(
      svg(
        "text",
        {
          class: "axis-label",
          x: pad.left - 8,
          y: y(t) + 4,
          "text-anchor": "end",
        },
        String(t),
      ),
    );
  }

  const tip = h(
    "p",
    { class: "chart__tip", "aria-live": "polite" },
    "Hover or focus a bar to see its value.",
  );
  data.forEach((d, i) => {
    const x = pad.left + i * slot + (slot - barW) / 2;
    const top = y(d.value);
    const barH = Math.max(0, pad.top + plotH - top);
    const r = Math.min(4, barW / 2, barH);
    // Rounded top corners only, square at the baseline.
    const path = barH
      ? `M${x},${top + barH}V${top + r}Q${x},${top} ${x + r},${top}H${x + barW - r}Q${x + barW},${top} ${x + barW},${top + r}V${top + barH}Z`
      : "";
    const text = `${d.label}: ${d.value} ${unit}`;
    const bar = svg("path", {
      class: "bar",
      d: path,
      tabindex: d.value ? 0 : -1,
    });
    bar.append(svg("title", {}, text));
    const showTip = () => (tip.textContent = text);
    bar.addEventListener("mouseenter", showTip);
    bar.addEventListener("focus", showTip);
    chart.append(bar);
    // Label every other bar, counting back from the last, so labels never collide.
    if ((data.length - 1 - i) % 2 === 0) {
      chart.append(
        svg(
          "text",
          {
            class: "axis-label",
            x: x + barW / 2,
            y: height - 6,
            "text-anchor": "middle",
          },
          d.label,
        ),
      );
    }
  });

  const table = h(
    "table",
    { class: "sr-only" },
    h("caption", {}, `${unit} per day`),
    h(
      "tbody",
      {},
      data.map((d) =>
        h(
          "tr",
          {},
          h("th", { scope: "row" }, d.label),
          h("td", {}, String(d.value)),
        ),
      ),
    ),
  );
  render(container, chart, tip, table);
}
