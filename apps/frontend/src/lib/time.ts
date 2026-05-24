/**
 * Timezone-aware formatting utilities.
 *
 * All backend timestamps are UTC ISO-8601. These helpers convert to the
 * browser's local timezone and append a short timezone indicator.
 */

const TIME_FORMATTER = new Intl.DateTimeFormat(undefined, {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const DATE_FORMATTER = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
});

function getTzAbbr(date: Date): string {
  // Extract timezone abbreviation from the locale string, e.g. "GMT+8" or "EST"
  const parts = new Intl.DateTimeFormat(undefined, {
    timeZoneName: "short",
  }).formatToParts(date);
  const tzPart = parts.find((p) => p.type === "timeZoneName");
  return tzPart?.value ?? "";
}

/** Format an ISO-8601 string as local HH:MM with TZ, e.g. "09:30 GMT+8" */
export function formatTimeLocal(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "—";
    const time = TIME_FORMATTER.format(d);
    const tz = getTzAbbr(d);
    return tz ? `${time} ${tz}` : time;
  } catch {
    return "—";
  }
}

/** Format an ISO-8601 string as local date + time, e.g. "May 25, 09:30 GMT+8" */
export function formatDateTimeLocal(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "—";
    const dt = DATE_TIME_FORMATTER.format(d);
    const tz = getTzAbbr(d);
    return tz ? `${dt} ${tz}` : dt;
  } catch {
    return "—";
  }
}

/** Format an ISO-8601 string as local date, e.g. "May 25" */
export function formatDateLocal(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "—";
    return DATE_FORMATTER.format(d);
  } catch {
    return "—";
  }
}

/** Extract HH:MM from an ISO-8601 string in local time (no TZ suffix). */
export function formatTimeLocalShort(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "—";
    return TIME_FORMATTER.format(d);
  } catch {
    return "—";
  }
}

/** Format a date string (YYYY-MM-DD) as local date */
export function formatDateOnly(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  try {
    const d = new Date(`${dateStr}T00:00:00Z`);
    if (isNaN(d.getTime())) return "—";
    return DATE_FORMATTER.format(d);
  } catch {
    return "—";
  }
}
