from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.mongodb import close_mongodb, init_mongodb
from app.db.session import init_db

configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if settings.MONGODB_URL:
        init_mongodb()
    yield
    close_mongodb()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-oriented enterprise document intelligence runtime with retrieval, agents, security and evaluation.",
    version="1.1.0",
    lifespan=lifespan,
)

origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    return {"service": settings.PROJECT_NAME, "version": "1.1.0", "status": "running"}
