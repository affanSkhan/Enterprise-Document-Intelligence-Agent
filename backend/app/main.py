from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from swagger_ui_bundle import swagger_ui_path

from app.api.auth_routes import router as auth_router
from app.api.multimodal_routes import router as multimodal_router
from app.api.platform_routes import router as platform_router
from app.api.routes import router as api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import bootstrap_admin, init_db
from app.observability.middleware import MetricsMiddleware
from app.observability.tracing import configure_tracing

configure_logging()
configure_tracing()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-oriented enterprise document intelligence runtime with retrieval, agents, security, evidence graphs, multimodal provenance and evaluation.",
    version="1.4.0",
    docs_url=None,
    redoc_url=None,
)

# FastAPI normally loads Swagger UI assets from a public CDN. Serve the bundled
# package assets locally so /docs works without external DNS/CDN access.
app.mount(
    "/docs-assets",
    StaticFiles(directory=str(swagger_ui_path)),
    name="docs-assets",
)

origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.add_middleware(MetricsMiddleware)
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(multimodal_router, prefix=settings.API_V1_PREFIX)
app.include_router(platform_router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
def startup():
    init_db()
    bootstrap_admin()


@app.get("/")
async def root():
    return {"service": settings.PROJECT_NAME, "version": "1.4.0", "status": "running"}


@app.get("/docs", include_in_schema=False)
async def swagger_docs():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url="/docs-assets/swagger-ui-bundle.js",
        swagger_css_url="/docs-assets/swagger-ui.css",
        swagger_favicon_url="/docs-assets/favicon.png",
    )


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
