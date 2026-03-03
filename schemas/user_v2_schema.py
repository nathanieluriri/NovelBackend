from schemas.imports import *
from schemas.bookmark_schema import BookMarkOutAsync
from schemas.likes_schema import LikeOut
from schemas.listing_schema import ListMetaOut
from schemas.reading_progress_schema import ReadingProgressOut


class InteractionTotals(BaseModel):
    totalLikes: int
    totalBookmarks: int


# class IndexedLikeOut(BaseModel):
#     index: int
#     item: LikeOut


# class IndexedBookmarkOut(BaseModel):
#     index: int
#     item: BookMarkOutAsync

class IndexedLikeOut(BaseModel):
    index: int
    item: LikeOut


class IndexedBookmarkOut(BaseModel):
    index: int
    item: BookMarkOutAsync


class UserLikesListOut(BaseModel):
    items: list[IndexedLikeOut]
    meta: ListMetaOut


class UserBookmarksListOut(BaseModel):
    items: list[IndexedBookmarkOut]
    meta: ListMetaOut


class UserDetailsV2Out(BaseModel):
    userId: str
    email: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    avatar: Optional[str] = None
    summary: InteractionTotals
    likes: list[IndexedLikeOut]
    bookmarks: list[IndexedBookmarkOut]
    readingProgress: Optional[ReadingProgressOut] = None
    likesMeta: ListMetaOut
    bookmarksMeta: ListMetaOut
