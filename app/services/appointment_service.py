from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.appointment_schema import AppointmentCreate, AppointmentUpdate
from app.utils.helpers import now_utc, serialize_doc


class AppointmentService:
    def __init__(self, db: AsyncIOMotorDatabase):
        """Keep a reference to the appointments collection."""
        self.collection = db.appointments

    async def list(self, status: str | None = None) -> list[dict]:
        """List appointments sorted by date, with an optional status filter."""
        query = {"status": status} if status else {}
        cursor = self.collection.find(query).sort("appointment_date", 1)
        return [serialize_doc(doc) async for doc in cursor]

    async def create(self, payload: AppointmentCreate) -> dict:
        """Insert a new appointment with the default scheduled status."""
        now = now_utc()
        doc = payload.model_dump() | {"status": "scheduled", "created_at": now, "updated_at": now}
        result = await self.collection.insert_one(doc)
        created = await self.collection.find_one({"_id": result.inserted_id})
        return serialize_doc(created)

    async def patch(self, appointment_id: str, payload: AppointmentUpdate) -> dict | None:
        """Update only the fields the client actually sent."""
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            return await self.get(appointment_id)
        updates["updated_at"] = now_utc()
        await self.collection.update_one({"_id": ObjectId(appointment_id)}, {"$set": updates})
        return await self.get(appointment_id)

    async def get(self, appointment_id: str) -> dict | None:
        """Fetch a single appointment by Mongo id."""
        return serialize_doc(await self.collection.find_one({"_id": ObjectId(appointment_id)}))
