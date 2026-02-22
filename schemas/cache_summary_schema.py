from schemas.imports import *
from schemas.chapter_schema import ChapterAccessType


class BookSummaryOut(BaseModel):
    id: str
    name: Optional[str] = None
    number: Optional[int] = None
    chapterCount: Optional[int] = 0
    dateCreated: Optional[str] = None
    dateUpdated: Optional[str] = None


class ChapterSummaryOut(BaseModel):
    id: str
    bookId: Optional[str] = None
    chapterLabel: Optional[str] = None
    number: Optional[int] = None
    accessType: Optional[ChapterAccessType] = None
    coverImage: Optional[str] = None
    pageCount: Optional[int] = 0
    dateCreated: Optional[str] = None
    dateUpdated: Optional[str] = None


class PageSummaryOut(BaseModel):
    id: str
    chapterId: Optional[str] = None
    status: Optional[str] = None
    number: Optional[int] = None
    textCount: Optional[int] = 0
    dateCreated: Optional[str] = None
    dateUpdated: Optional[str] = None
