from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.call_schema import OutboundCallRequest
from app.services.twilio_service import TwilioService
from app.utils.helpers import now_utc, serialize_doc


class CallService:
    def __init__(self, db: AsyncIOMotorDatabase, twilio_service: TwilioService):
        """Keep the Mongo collections and Twilio wrapper this service needs."""
        self.collection = db.calls
        self.appointments = db.appointments
        self.twilio_service = twilio_service

    async def create_outbound(self, payload: OutboundCallRequest) -> dict:
        """Save the call first, then update it with Twilio's dialing result."""
        now = now_utc()
        doc = payload.model_dump() | {
            "status": "queued",
            "transcript": [],
            "summary": "",
            "outcome": "pending",
            "sentiment": None,
            "duration": 0,
            "latency_ms": None,
            "twilio_call_sid": None,
            "created_at": now,
            "updated_at": now,
        }
        result = await self.collection.insert_one(doc)
        call_id = str(result.inserted_id)
        start_result = await self.twilio_service.start_outbound_call(
            payload.phone_number,
            call_id,
            payload.system_type,
        )
        updates = {"updated_at": now_utc()}
        if start_result.ok:
            updates |= {"twilio_call_sid": start_result.provider_call_id, "status": "ringing"}
        else:
            updates |= {
                "status": "failed",
                "outcome": "failed",
                "provider_error": start_result.error,
                "provider_error_code": start_result.error_code,
            }
        await self.collection.update_one({"_id": result.inserted_id}, {"$set": updates})
        return await self.get(call_id)

    async def list(self) -> list[dict]:
        """Return the newest calls, serialized for API responses."""
        cursor = self.collection.find({}).sort("created_at", -1).limit(100)
        return [serialize_doc(doc) async for doc in cursor]

    async def get(self, call_id: str) -> dict | None:
        """Find one call by Mongo id and convert Mongo-only values to strings."""
        return serialize_doc(await self.collection.find_one({"_id": ObjectId(call_id)}))

    async def append_transcript(self, call_id: str, speaker: str, text: str) -> None:
        """Add a transcript turn and mark the call as active."""
        await self.collection.update_one(
            {"_id": ObjectId(call_id)},
            {
                "$push": {"transcript": {"speaker": speaker, "text": text, "timestamp": now_utc()}},
                "$set": {"status": "in_progress", "updated_at": now_utc()},
            },
        )

    async def complete(self, call_id: str, summary: dict, latency_ms: int | None = None) -> dict | None:
        """Finalize the call, persist summary metrics, and sync appointment status."""
        call = await self.get(call_id)
        if not call:
            return None
        duration = int((now_utc() - _parse_dt(call["created_at"])).total_seconds())
        updates = {
            "summary": summary.get("summary", ""),
            "outcome": summary.get("outcome", "pending"),
            "sentiment": summary.get("sentiment"),
            "duration": duration,
            "latency_ms": latency_ms,
            "status": "completed",
            "updated_at": now_utc(),
        }
        await self.collection.update_one({"_id": ObjectId(call_id)}, {"$set": updates})
        appointment_id = call.get("appointment_id")
        outcome = updates["outcome"]
        if appointment_id and outcome in {"confirmed", "rescheduled", "cancelled", "failed"}:
            await self.appointments.update_one(
                {"_id": ObjectId(appointment_id)},
                {"$set": {"status": outcome, "updated_at": now_utc()}},
            )
        return await self.get(call_id)


def _parse_dt(value):
    """Handle dates coming either from Mongo as datetimes or from APIs as strings."""
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
