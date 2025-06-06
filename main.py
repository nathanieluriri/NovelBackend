from fastapi import FastAPI,Depends
from security.auth import verify_admin_token
from api.v1 import user,book,bookmark,like,chapter,page,admin
from security.auth import verify_token
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Mie Novel-app FastAPI Backend",summary="""Backend for the "Mie Novel-app", providing RESTful endpoints to manage users, novel content (books, chapters, pages), bookmarks, and likes. Features JWT-based authentication supporting both traditional credentials and Google sign-in, including token refresh capabilities.""")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)
    
user_dependencies=[Depends(verify_token)]
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(user.router, prefix="/api/v1/user", tags=["User"])
app.include_router(book.router,prefix="/api/v1/book", tags=["Book"],dependencies=[Depends(verify_admin_token)])
app.include_router(bookmark.router,prefix="/api/v1/bookmark", tags=["Bookmark"])
app.include_router(like.router,prefix="/api/v1/like", tags=["Like"])
app.include_router(chapter.router,prefix="/api/v1/chapter", tags=["Chapter"],)
app.include_router(page.router,prefix="/api/v1/page", tags=["Page"])

