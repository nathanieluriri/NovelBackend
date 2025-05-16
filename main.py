from fastapi import FastAPI, Depends
from api.v1 import user,book,bookmark,like,chapter,page,admin
from security.auth import verify_token
app = FastAPI(title="Mei Novel-app FastAPI Backend",
              servers=
    [
        {"url": "https://novel-backend-eight.vercel.app/", "description": "Production server"},
        {"url": "http://127.0.0.1:8000/", "description": "Local development server"},
        
        {"url": "https://novelbackend.onrender.com/", "description": "Sandbox server"},
        
    ],
    summary="""Backend for the "Mei Novel-app", providing RESTful endpoints to manage users, novel content (books, chapters, pages), bookmarks, and likes. Features JWT-based authentication supporting both traditional credentials and Google sign-in, including token refresh capabilities."""
    
    )
dependencies=[Depends(verify_token)]
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(user.router, prefix="/api/v1/user", tags=["User"])
app.include_router(book.router,prefix="/api/v1/book", tags=["Book"],dependencies=[Depends(verify_token)])
app.include_router(bookmark.router,prefix="/api/v1/bookmark", tags=["Bookmark"],dependencies=[Depends(verify_token)])
app.include_router(like.router,prefix="/api/v1/like", tags=["Like"],dependencies=[Depends(verify_token)])
app.include_router(chapter.router,prefix="/api/v1/chapter", tags=["Chapter"],dependencies=[Depends(verify_token)])
app.include_router(page.router,prefix="/api/v1/page", tags=["Page"],dependencies=[Depends(verify_token)])