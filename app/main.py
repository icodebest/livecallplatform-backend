from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from app.api.routes import appointments, auth, dashboard, sessions
from app.core.config import get_settings
from app.core.database import close_mongo_connection, connect_to_mongo
from app.core.logger import logger, setup_logging
from app.websocket import session_stream


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bring shared infrastructure up before requests, then close it cleanly."""
    setup_logging()
    await connect_to_mongo()
    logger.info("Application started")
    yield
    await close_mongo_connection()


settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0", root_path=settings.api_root_path.rstrip("/"), lifespan=lifespan)


def cors_origins() -> list[str]:
    configured = [settings.frontend_url, *settings.frontend_urls.split(",")]
    origins = {origin.strip().rstrip("/") for origin in configured if origin.strip()}
    origins.update({"http://localhost:5173", "http://localhost:5174"})
    return sorted(origins)


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|192\.168\.\d+\.\d+):517\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(appointments.router)
app.include_router(dashboard.router)
app.include_router(session_stream.router)

app.include_router(auth.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(session_stream.router, prefix="/api")


@app.get("/health")
async def health():
    """Small health check used by humans, monitors, or deployment platforms."""
    return {"status": "ok", "service": settings.app_name}


@app.get("/")
async def root():
    """Identify the API when the backend is reached without a route."""
    return {"status": "ok", "service": settings.app_name, "docs": f"{settings.api_root_path.rstrip('/')}/docs"}


@app.get("/api")
async def api_root():
    """Identify the API when reached through the production /api prefix."""
    return {"status": "ok", "service": settings.app_name, "docs": "/api/docs"}


@app.get("/api/health")
async def api_health():
    """Health check for deployments that route API traffic through /api."""
    return {"status": "ok", "service": settings.app_name}


@app.get("/api/openapi.json", include_in_schema=False)
async def prefixed_openapi():
    """Serve OpenAPI JSON for proxies that preserve the /api prefix."""
    return app.openapi()


@app.get("/api/docs", include_in_schema=False)
async def prefixed_docs():
    """Serve Swagger UI for proxies that preserve the /api prefix."""
    return get_swagger_ui_html(openapi_url="/api/openapi.json", title=f"{settings.app_name} - Swagger UI")
