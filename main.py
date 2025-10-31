from fastapi import FastAPI,Depends
from fastapi.responses import JSONResponse
from security.auth import verify_admin_token
from api.v1 import user,book,bookmark,like,chapter,page,admin,comments,payment
from security.auth import verify_token
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(root_path="/api/v1",title="Mie Novel-app FastAPI Backend",summary="""Backend for the "Mie Novel-app", providing RESTful endpoints to manage users, novel content (books, chapters, pages), bookmarks, and likes. Features JWT-based authentication supporting both traditional credentials and Google sign-in, including token refresh capabilities.""")
from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key="some-random-string")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
    
    
user_dependencies=[Depends(verify_token)]
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(book.router,prefix="/book", tags=["Book"],dependencies=[Depends(verify_admin_token)])
app.include_router(bookmark.router,prefix="/bookmark", tags=["Bookmark"])
app.include_router(like.router,prefix="/like", tags=["Like"])
app.include_router(chapter.router,prefix="/chapter", tags=["Chapter"],)
app.include_router(page.router,prefix="/page", tags=["Page"])
app.include_router(comments.router,prefix="/comment",tags=['Comment'])
app.include_router(payment.router,prefix="/payment",tags=["Payment"])

