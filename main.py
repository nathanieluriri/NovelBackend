from fastapi import FastAPI, Depends
from api.v1 import user,book,bookmark,like,chapter,page
from security.auth import verify_token
app = FastAPI(title="Mei FastAPI Backend",
              servers=
    [
        {"url": "http://127.0.0.1:8000/", "description": "Local development server"},
        {"url": "https://api.example.com", "description": "Production server"},
        {"url": "http://127.0.0.1:8000/", "description": "Sandbox server"},
        
    ],
    summary="hello"
    
    )

app.include_router(user.router, prefix="/api/v1/user", tags=["User"],dependencies=[Depends(verify_token)])
app.include_router(book.router,prefix="/api/v1/book", tags=["Book"])
app.include_router(bookmark.router,prefix="/api/v1/bookmark", tags=["Bookmark"])
app.include_router(like.router,prefix="/api/v1/like", tags=["Like"])
app.include_router(chapter.router,prefix="/api/v1/chapter", tags=["Chapter"])
app.include_router(page.router,prefix="/api/v1/page", tags=["Page"])