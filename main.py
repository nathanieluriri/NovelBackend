from fastapi import FastAPI
from api.v1 import user,book,bookmark

app = FastAPI(title="Modular FastAPI")

app.include_router(user.router, prefix="/api/v1/user", tags=["User"])
app.include_router(book.router,prefix="/api/v1/book", tags=["Book"])
app.include_router(bookmark.router,prefix="/api/v1/bookmark", tags=["Bookmark"])