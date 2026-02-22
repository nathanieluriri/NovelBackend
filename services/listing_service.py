from typing import Any, Sequence

from schemas.listing_schema import ListMetaOut, ListSummaryOut


def clamp_limit(limit: int) -> int:
    return min(max(limit, 1), 100)


def build_meta(*, skip: int, limit: int, returned: int, total: int) -> ListMetaOut:
    return ListMetaOut(
        skip=skip,
        limit=limit,
        returned=returned,
        total=total,
        hasMore=(skip + returned < total),
    )


def build_summary(*, returned: int, total: int) -> ListSummaryOut:
    return ListSummaryOut(totalItems=total, returnedItems=returned)


def build_indexed_items(items: Sequence[Any], *, skip: int) -> list[dict[str, Any]]:
    return [{"index": skip + i + 1, "item": item} for i, item in enumerate(items)]


def build_list_payload(items: Sequence[Any], *, skip: int, limit: int, total: int) -> dict[str, Any]:
    returned = len(items)
    return {
        "items": build_indexed_items(items, skip=skip),
        "meta": build_meta(skip=skip, limit=limit, returned=returned, total=total),
        "summary": build_summary(returned=returned, total=total),
    }
