from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
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

# swagger-ui-bundle 1.1.0 ships Swagger UI 4.15.5. Keep the generated schema
# at OpenAPI 3.0.3 and normalize binary upload fields to the OAS 3.0
# `format: binary` representation so Swagger UI renders a native file picker.
app.openapi_version = "3.0.3"


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["openapi"] = "3.0.3"

    # Newer FastAPI/OpenAPI 3.1 schemas may describe uploads using
    # contentMediaType. Swagger UI 4.x expects the OpenAPI 3.0 binary form.
    for component in schema.get("components", {}).get("schemas", {}).values():
        properties = component.get("properties", {}) if isinstance(component, dict) else {}
        for prop in properties.values():
            if not isinstance(prop, dict):
                continue
            if prop.get("contentMediaType") == "application/octet-stream":
                prop.pop("contentMediaType", None)
                prop["type"] = "string"
                prop["format"] = "binary"
            items = prop.get("items")
            if isinstance(items, dict) and items.get("contentMediaType") == "application/octet-stream":
                items.pop("contentMediaType", None)
                items["type"] = "string"
                items["format"] = "binary"

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi

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


def custom_openapi() -> dict:
    """Generate a Swagger UI 4-compatible OpenAPI document.

    Recent FastAPI/Pydantic versions describe uploaded files with the JSON
    Schema ``contentMediaType`` keyword.  Swagger UI 4 expects OpenAPI 3.0's
    ``format: binary`` instead, otherwise it shows a text input rather than a
    file chooser.
    """
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["openapi"] = app.openapi_version
    for component in schema.get("components", {}).get("schemas", {}).values():
        for property_schema in component.get("properties", {}).values():
            if property_schema.get("contentMediaType") == "application/octet-stream":
                property_schema.pop("contentMediaType", None)
                property_schema["format"] = "binary"

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


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
