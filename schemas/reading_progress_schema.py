from schemas.imports import *
from schemas.cache_summary_schema import ChapterSummaryOut, PageSummaryOut


class ReadingProgressRecord(BaseModel):
    userId: str
    chapterId: str
    pageId: str
    dateCreated: Optional[str] = None
    dateUpdated: Optional[str] = None


class ReadingProgressOut(BaseModel):
    userId: str
    chapterId: str
    pageId: str
    dateUpdated: Optional[str] = None
    chapterSummary: Optional[ChapterSummaryOut] = None
    pageSummary: Optional[PageSummaryOut] = None
