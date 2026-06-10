import { HttpError } from "./errors";

/**
 * v2 wire contract (see ../nextjs-migration/schema.md §1–3).
 * Success envelope: exactly 3 keys, in order: success, message, data.
 * Error envelope: success, message, data:null, errors? (only when present).
 */

export function successBody(data: unknown, message = "Success") {
  return { success: true, message, data };
}

export function success(data: unknown, status = 200): Response {
  return Response.json(successBody(data), { status });
}

export function errorResponse(status: number, message: string, errors?: unknown): Response {
  const body: Record<string, unknown> = { success: false, message, data: null };
  if (errors !== undefined) body.errors = errors;
  return Response.json(body, { status });
}

/** Clamp limit to 1..100 — the clamped value is echoed in meta. */
export function clampLimit(limit: number): number {
  if (Number.isNaN(limit)) return 20;
  return Math.max(1, Math.min(100, Math.trunc(limit)));
}

/** Parse skip/limit query params with legacy semantics (skip<0 → 400). */
export function parseSkipLimit(req: Request, defaultLimit = 20): { skip: number; limit: number } {
  const sp = new URL(req.url).searchParams;
  const skip = parseInt(sp.get("skip") ?? "0", 10);
  const limit = clampLimit(parseInt(sp.get("limit") ?? String(defaultLimit), 10));
  if (Number.isNaN(skip) || skip < 0) throw new HttpError(400, "skip must be >= 0");
  return { skip, limit };
}

export interface ListMeta {
  skip: number;
  limit: number;
  returned: number;
  total: number;
  hasMore: boolean;
}

export interface PaginatedList<T> {
  items: T[];
  meta: ListMeta;
  summary: { totalItems: number; returnedItems: number };
}

/** PaginatedListOut — items FLAT (no index wrapper). Field order: items, meta, summary. */
export function paginate<T>(items: T[], skip: number, limit: number, total: number): PaginatedList<T> {
  const returned = items.length;
  return {
    items,
    meta: { skip, limit, returned, total, hasMore: skip + returned < total },
    summary: { totalItems: total, returnedItems: returned },
  };
}

/**
 * Indexed-item variant — wraps each item as `{ index, item }` with a 1-based,
 * skip-offset index, matching the ONLY place legacy emits this shape:
 * UserDetailsV2Out's `IndexedLikeOut(index=i + 1, ...)` (api/v2/user.py) and the
 * commented-out `build_indexed_items` (`skip + i + 1`, listing_service.py).
 * NOTE: the /user/likes and /user/bookmarks list routes use flat `paginate`
 * (legacy build_list_payload returns list(items)); /user/details indexes inline.
 */
export function paginateIndexed<T>(items: T[], skip: number, limit: number, total: number) {
  const wrapped = items.map((item, i) => ({ index: skip + i + 1, item }));
  const returned = items.length;
  return {
    items: wrapped,
    meta: { skip, limit, returned, total, hasMore: skip + returned < total },
  };
}

export function buildListMeta(skip: number, limit: number, returned: number, total: number): ListMeta {
  return { skip, limit, returned, total, hasMore: skip + returned < total };
}
