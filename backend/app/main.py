from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth_routes import router as auth_router
from app.api.routes import router as api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import bootstrap_admin, init_db

configure_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-oriented enterprise document intelligence runtime with retrieval, agents, security and evaluation.",
    version="1.1.0",
)

origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
def startup():
    init_db()
    bootstrap_admin()


@app.get("/")
async def root():
    return {"service": settings.PROJECT_NAME, "version": "1.1.0", "status": "running"}
