from fastapi import FastAPI
from database import Base, engine
from routers import user, auth, post
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    #Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:8100",
    "http://56.228.35.186",
    "https://56.228.35.186",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(post.router, prefix="/api")