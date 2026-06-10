/**
 * Wire contract requires ISO-8601 UTC strings with a `+00:00` offset, never `Z`
 * (see ../nextjs-migration/schema.md §0.5). Legacy data stores three formats:
 * ISO strings, epoch integers (seconds), and BSON dates — all normalize here.
 */
export function toIsoOffset(d: Date | string | number | null | undefined): string | null {
  if (d === null || d === undefined) return null;
  let date: Date;
  if (typeof d === "number") {
    // epoch seconds (legacy reactions/author_rooms/bundles) vs milliseconds
    date = new Date(d < 1e12 ? d * 1000 : d);
  } else if (typeof d === "string") {
    const t = Date.parse(d);
    if (Number.isNaN(t)) return d; // unparseable legacy string — pass through untouched
    date = new Date(t);
  } else {
    date = d;
  }
  // Python's datetime.isoformat() (legacy normalize_datetime_to_iso) omits the
  // fractional part for whole-second values, e.g. epoch ints →
  // '2025-06-10T12:00:00+00:00'. JS toISOString() always appends '.000', so we
  // strip a zero-millisecond fraction to match the legacy wire string for the
  // common case (every epoch-seconds timestamp is whole-second).
  const iso = date.toISOString();
  return iso.endsWith(".000Z") ? iso.slice(0, -5) + "+00:00" : iso.replace("Z", "+00:00");
}

export function nowIso(): string {
  return toIsoOffset(new Date()) as string;
}

export function nowEpoch(): number {
  return Math.floor(Date.now() / 1000);
}

/** True when `dateCreated` (ISO string) is older than `days` days. */
export function isOlderThanDays(iso: string | null | undefined, days: number): boolean {
  if (!iso) return true;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return true;
  return Date.now() - t > days * 24 * 60 * 60 * 1000;
}
