from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.session_schema import SessionCreate
from app.utils.helpers import now_utc, serialize_doc


class SessionService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.calls
        self.appointments = db.appointments

    async def create(self, payload: SessionCreate, user: dict) -> dict:
        now = now_utc()
        doc = payload.model_dump() | {
            "user_id": user["_id"],
            "status": "created",
            "transcript": [],
            "summary": "",
            "outcome": "pending",
            "sentiment": None,
            "appointment_update": {},
            "duration": 0,
            "latency_ms": None,
            "latency_samples": [],
            "created_at": now,
            "updated_at": now,
        }
        result = await self.collection.insert_one(doc)
        return await self.get(str(result.inserted_id), user)

    async def list(self, user: dict) -> list[dict]:
        cursor = self.collection.find({"user_id": user["_id"]}).sort("created_at", -1).limit(100)
        return [serialize_doc(doc) async for doc in cursor]

    async def get(self, session_id: str, user: dict) -> dict | None:
        object_id = _object_id(session_id)
        return serialize_doc(await self.collection.find_one({"_id": object_id, "user_id": user["_id"]}))

    async def start(self, session_id: str, user: dict) -> None:
        await self.collection.update_one(
            {"_id": _object_id(session_id), "user_id": user["_id"]},
            {"$set": {"status": "in_progress", "started_at": now_utc(), "updated_at": now_utc()}},
        )

    async def append_transcript(self, session_id: str, user: dict, speaker: str, text: str) -> None:
        await self.collection.update_one(
            {"_id": _object_id(session_id), "user_id": user["_id"]},
            {
                "$push": {"transcript": {"speaker": speaker, "text": text, "timestamp": now_utc()}},
                "$set": {"status": "in_progress", "updated_at": now_utc()},
            },
        )

    async def record_latency(self, session_id: str, user: dict, latency_ms: int) -> None:
        await self.collection.update_one(
            {"_id": _object_id(session_id), "user_id": user["_id"]},
            {"$push": {"latency_samples": latency_ms}, "$set": {"latency_ms": latency_ms, "updated_at": now_utc()}},
        )

    async def complete(self, session_id: str, user: dict, summary: dict) -> dict | None:
        session = await self.get(session_id, user)
        if not session:
            return None
        started_at = session.get("started_at") or session["created_at"]
        duration = int((now_utc() - _parse_dt(started_at)).total_seconds())
        samples = session.get("latency_samples") or []
        updates = {
            "summary": summary.get("summary", ""),
            "outcome": summary.get("outcome", "pending"),
            "sentiment": summary.get("sentiment"),
            "appointment_update": summary.get("appointment_update", {}),
            "duration": duration,
            "latency_ms": round(sum(samples) / len(samples)) if samples else session.get("latency_ms"),
            "status": "completed",
            "updated_at": now_utc(),
        }
        await self.collection.update_one({"_id": _object_id(session_id), "user_id": user["_id"]}, {"$set": updates})
        appointment_id = session.get("appointment_id")
        if appointment_id and updates["outcome"] in {"confirmed", "rescheduled", "cancelled", "failed"}:
            await self.appointments.update_one(
                {"_id": _object_id(appointment_id), "user_id": user["_id"]},
                {"$set": {"status": updates["outcome"], "updated_at": now_utc()}},
            )
        return await self.get(session_id, user)


def _object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId as exc:
        raise HTTPException(status_code=400, detail="Invalid id") from exc


def _parse_dt(value):
    from datetime import datetime, timezone

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
