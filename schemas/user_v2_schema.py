from schemas.imports import *
from schemas.bookmark_schema import BookMarkOutAsync
from schemas.likes_schema import LikeOut


class InteractionTotals(BaseModel):
    totalLikes: int
    totalBookmarks: int


class ListMeta(BaseModel):
    skip: int
    limit: int
    returned: int
    total: int
    hasMore: bool


class IndexedLikeOut(BaseModel):
    index: int
    item: LikeOut


class IndexedBookmarkOut(BaseModel):
    index: int
    item: BookMarkOutAsync


class UserLikesListOut(BaseModel):
    items: list[IndexedLikeOut]
    meta: ListMeta


class UserBookmarksListOut(BaseModel):
    items: list[IndexedBookmarkOut]
    meta: ListMeta


class UserDetailsV2Out(BaseModel):
    summary: InteractionTotals
    likes: list[IndexedLikeOut]
    bookmarks: list[IndexedBookmarkOut]
    likesMeta: ListMeta
    bookmarksMeta: ListMeta
