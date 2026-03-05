from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.models import User, File
from app.database import Base
from app.routers import files, admin
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000", "http://localhost:8001"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(files.router)
app.include_router(admin.router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME}