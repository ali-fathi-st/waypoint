/**
 * Display helpers. The API sends:
 * - timestamps as ISO 8601 strings in UTC ("2026-11-10T15:04:00Z")
 * - calendar dates as "YYYY-MM-DD" (applied_at, follow_up_at)
 * Calendar dates have no time zone, so they are never passed to `new Date()`
 * directly (that would read them as UTC midnight and show the previous day in
 * Edmonton).
 */
const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;

function parseDateOnly(value) {
  const [y, m, d] = value.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function toDate(value) {
  return DATE_ONLY.test(value) ? parseDateOnly(value) : new Date(value);
}

const dateFmt = new Intl.DateTimeFormat("en-CA", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

const shortDateFmt = new Intl.DateTimeFormat("en-CA", {
  month: "short",
  day: "numeric",
});

const dateTimeFmt = new Intl.DateTimeFormat("en-CA", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

export function formatDate(value) {
  if (!value) return "—";
  return dateFmt.format(toDate(value));
}

export function formatShortDate(value) {
  if (!value) return "—";
  return shortDateFmt.format(toDate(value));
}

export function formatDateTime(value) {
  if (!value) return "—";
  return dateTimeFmt.format(toDate(value));
}

/** "Today", "Yesterday", "3 days ago", or a date for anything older than 30 days. */
export function formatRelative(value, now = new Date()) {
  if (!value) return "—";
  const days = calendarDaysBetween(toDate(value), now);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 30) return `${days} days ago`;
  return formatDate(value);
}

/** Whole calendar days from `a` to `b` in local time (b - a). */
export function calendarDaysBetween(a, b) {
  const start = new Date(a.getFullYear(), a.getMonth(), a.getDate()).getTime();
  const end = new Date(b.getFullYear(), b.getMonth(), b.getDate()).getTime();
  return Math.round((end - start) / 86_400_000);
}

/** Days until a calendar date. Negative when it has passed. */
export function daysUntil(dateOnly, now = new Date()) {
  return calendarDaysBetween(now, parseDateOnly(dateOnly));
}

/** Today as "YYYY-MM-DD" in local time. */
export function todayDateOnly(now = new Date()) {
  return toDateOnly(now);
}

export function toDateOnly(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function addDays(dateOnly, days) {
  const d = parseDateOnly(dateOnly);
  d.setDate(d.getDate() + days);
  return toDateOnly(d);
}

export function formatSalary(min, max, currency) {
  if (min == null && max == null) return null;
  const fmt = new Intl.NumberFormat("en-CA", {
    style: "currency",
    currency: currency ?? "CAD",
    maximumFractionDigits: 0,
    notation: "compact",
  });
  if (min != null && max != null && min !== max)
    return `${fmt.format(min)}–${fmt.format(max)}`;
  return fmt.format(min ?? max);
}

export function formatPercent(ratio) {
  if (ratio == null || Number.isNaN(ratio)) return "—";
  return `${Math.round(ratio * 100)}%`;
}

export function formatBytes(bytes) {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function pluralize(count, one, many = `${one}s`) {
  return `${count} ${count === 1 ? one : many}`;
}
