from typing import Generic, TypeVar

from schemas.imports import *

T = TypeVar("T")


class ListSummaryOut(BaseModel):
    totalItems: int
    returnedItems: int


class ListMetaOut(BaseModel):
    skip: int
    limit: int
    returned: int
    total: int
    hasMore: bool


class IndexedItemOut(BaseModel, Generic[T]):
    index: int
    item: T


class PaginatedListOut(BaseModel, Generic[T]):
    items: list[IndexedItemOut[T]]
    meta: ListMetaOut
    summary: ListSummaryOut
