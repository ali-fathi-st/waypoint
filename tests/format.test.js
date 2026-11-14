import { test } from "node:test";
import assert from "node:assert/strict";
import {
  addDays,
  daysUntil,
  formatRelative,
  formatSalary,
  todayDateOnly,
} from "../frontend/js/lib/format.js";

test("adds days across a month boundary", () => {
  assert.equal(addDays("2026-11-24", 14), "2026-12-08");
});

test("counts calendar days until a date", () => {
  const now = new Date(2026, 10, 10, 21, 0);
  assert.equal(daysUntil("2026-11-10", now), 0);
  assert.equal(daysUntil("2026-11-24", now), 14);
  assert.equal(daysUntil("2026-11-08", now), -2);
});

test("describes recent days in words", () => {
  const now = new Date(2026, 10, 10, 12);
  assert.equal(
    formatRelative(new Date(2026, 10, 10, 8).toISOString(), now),
    "Today",
  );
  assert.equal(
    formatRelative(new Date(2026, 10, 9, 8).toISOString(), now),
    "Yesterday",
  );
  assert.equal(
    formatRelative(new Date(2026, 10, 5, 8).toISOString(), now),
    "5 days ago",
  );
});

test("gives today as YYYY-MM-DD", () => {
  assert.equal(todayDateOnly(new Date(2026, 0, 5)), "2026-01-05");
});

test("formats salary ranges and handles missing values", () => {
  assert.equal(formatSalary(null, null, null), null);
  assert.match(formatSalary(85000, 105000, "CAD"), /85K.*105K/);
});
