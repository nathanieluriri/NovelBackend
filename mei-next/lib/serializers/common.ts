/**
 * Shared internal helpers for the pure doc→wire serializers.
 * Legacy Mongo data is heterogeneous, so all serializers accept loose docs
 * (`.lean()` results) and coerce defensively. NOT re-exported from the barrel.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */
export type AnyDoc = Record<string, any>;

/** `id = String(_id)` — prefers an already-stringified `id` key, then `_id`. */
export function docId(doc: AnyDoc): string {
  return String(doc?.id ?? doc?._id ?? "");
}

/** Same as docId but yields null when neither `id` nor `_id` exists. */
export function idOrNull(doc: AnyDoc): string | null {
  const raw = doc?.id ?? doc?._id;
  return raw === null || raw === undefined ? null : String(raw);
}

export function strOrNull(v: unknown): string | null {
  return v === null || v === undefined ? null : String(v);
}

export function numOrNull(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isNaN(n) ? null : n;
}

export function numOrDefault(v: unknown, fallback: number): number {
  const n = numOrNull(v);
  return n === null ? fallback : n;
}

export function strArrOrNull(v: unknown): string[] | null {
  return Array.isArray(v) ? v.map((x) => String(x)) : null;
}
