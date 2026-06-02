from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:5174"],
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


@app.get("/health")
async def health():
    """Small health check used by humans, monitors, or deployment platforms."""
    return {"status": "ok", "service": settings.app_name}
