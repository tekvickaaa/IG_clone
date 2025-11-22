from fastapi import FastAPI
from database import Base, engine
from routers import user, auth, post, story,chat,reels
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    #Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine, checkfirst=True)
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(auth.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(post.router, prefix="/api")
app.include_router(story.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(reels.router, prefix="/api")