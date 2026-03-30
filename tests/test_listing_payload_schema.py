from pydantic import BaseModel

from schemas.listing_schema import PaginatedListOut
from services.listing_service import build_list_payload


class DummyItem(BaseModel):
    value: str


def test_build_list_payload_returns_raw_items_shape():
    items = [DummyItem(value="a"), DummyItem(value="b")]

    payload = build_list_payload(items, skip=0, limit=20, total=5)
    assert isinstance(payload, PaginatedListOut)
    assert payload.items[0].value == "a"
    assert payload.items[1].value == "b"
    assert payload.meta.returned == 2
    assert payload.meta.total == 5
    assert payload.meta.hasMore is True
