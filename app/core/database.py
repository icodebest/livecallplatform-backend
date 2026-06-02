from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import get_settings


class Mongo:
    """Small process-wide holder for the async Mongo client and database."""
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


mongo = Mongo()


async def connect_to_mongo() -> None:
    """Open MongoDB, verify it responds, and prepare indexes used by queries."""
    settings = get_settings()
    mongo.client = AsyncIOMotorClient(settings.mongodb_uri)
    mongo.db = mongo.client[settings.mongodb_db]
    await mongo.db.command("ping")
    await ensure_indexes()


async def close_mongo_connection() -> None:
    """Close the Mongo client during FastAPI shutdown."""
    if mongo.client:
        mongo.client.close()


def get_db() -> AsyncIOMotorDatabase:
    """Return the initialized database or fail fast if startup did not run."""
    if mongo.db is None:
        raise RuntimeError("MongoDB has not been initialized")
    return mongo.db


async def ensure_indexes() -> None:
    """Create common lookup indexes for appointment, session, and dashboard queries."""
    if mongo.db is None:
        return
    await mongo.db.appointments.create_index("status")
    await mongo.db.appointments.create_index("user_id")
    await mongo.db.calls.create_index("created_at")
    await mongo.db.calls.create_index("system_type")
    await mongo.db.calls.create_index("user_id")
    await mongo.db.users.create_index("email", unique=True)
