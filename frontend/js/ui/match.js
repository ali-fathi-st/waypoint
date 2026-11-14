/**
 * How the match score is shown.
 * - scoreMeter(): the compact number + bar used in lists.
 * - fitLedger(): the full explanation on the job page. Each factor's points
 *   (weight x how well it's met) add up to the total, so nothing about the
 *   score is hidden.
 */
import { h } from "../lib/dom.js";

export function scoreMeter(score) {
  if (score === null || score === undefined)
    return h("span", { class: "small muted" }, "Not scored");
  return h(
    "span",
    {
      class: "score",
      role: "img",
      "aria-label": `Match score ${score} out of 100`,
    },
    h("span", { class: "score__num" }, String(score)),
    h("span", { class: "score__bar" }, h("span", { style: `width:${score}%` })),
  );
}

export function fitLedger(match) {
  const rows = match.factors.filter((f) => f.weight > 0);
  return h(
    "div",
    { class: "ledger" },
    h(
      "div",
      { class: "ledger__top" },
      h(
        "div",
        {},
        h("p", { class: "small muted" }, "Match score"),
        h(
          "p",
          { class: "ledger__score" },
          String(match.score),
          h("small", {}, " / 100"),
        ),
      ),
      h("p", { class: "ledger__summary" }, match.summary),
    ),
    h(
      "table",
      {},
      h("caption", { class: "sr-only" }, "How the match score adds up"),
      h(
        "thead",
        {},
        h(
          "tr",
          {},
          h("th", { scope: "col" }, "Factor"),
          h("th", { scope: "col", class: "pts" }, "Points"),
        ),
      ),
      h(
        "tbody",
        {},
        rows.map((f) => {
          const max = Math.round(f.weight * 100);
          const earned = Math.round(f.weight * f.score * 100);
          return h(
            "tr",
            {},
            h(
              "th",
              { scope: "row" },
              h("strong", {}, f.label),
              h("span", {}, f.detail),
              h(
                "span",
                {
                  class: "meter",
                  role: "img",
                  "aria-label": `${Math.round(f.score * 100)}% met`,
                },
                h("span", { style: `width:${f.score * 100}%` }),
              ),
            ),
            h(
              "td",
              { class: "pts" },
              String(earned),
              h("span", {}, ` / ${max}`),
            ),
          );
        }),
      ),
      h(
        "tfoot",
        {},
        h(
          "tr",
          {},
          h("th", { scope: "row" }, "Total"),
          h("td", { class: "pts" }, String(match.score)),
        ),
      ),
    ),
    h(
      "p",
      { class: "ledger__note" },
      "A ranking aid built from your profile, not a prediction of whether you'll be hired.",
    ),
  );
}
