from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.api.endpoints import router as api_router
from app.db.seed import seed_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with AsyncSessionLocal() as session:
        await seed_db(session)
    yield
    # Shutdown (nothing to do)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="SevaFlow Queue Management System API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
