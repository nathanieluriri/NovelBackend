from pydantic import BaseModel

from schemas.listing_schema import PaginatedListOut
from services.listing_service import build_list_payload


class DummyItem(BaseModel):
    value: str


def test_build_list_payload_returns_raw_items_shape():
    items = [DummyItem(value="a"), DummyItem(value="b")]

    payload = build_list_payload(items, skip=0, limit=20, total=5)
    parsed = PaginatedListOut[DummyItem].model_validate(payload)

    assert parsed.items[0].value == "a"
    assert parsed.items[1].value == "b"
    assert parsed.meta.returned == 2
    assert parsed.meta.total == 5
    assert parsed.meta.hasMore is True

