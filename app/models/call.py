from typing import Literal
from pydantic import BaseModel, Field
from datetime import datetime


SystemType = Literal["realtime", "modular"]
CallOutcome = Literal["pending", "confirmed", "rescheduled", "cancelled", "failed", "voicemail", "escalated"]


class TranscriptTurn(BaseModel):
    """One line of conversation captured during a phone call."""
    speaker: Literal["ai", "patient", "system"]
    text: str
    timestamp: datetime


class CallModel(BaseModel):
    """Stored Mongo shape for an outbound appointment call."""
    patient_name: str
    phone_number: str
    doctor_name: str | None = None
    appointment_id: str | None = None
    system_type: SystemType
    status: Literal["queued", "ringing", "in_progress", "completed", "failed"] = "queued"
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    summary: str = ""
    outcome: CallOutcome = "pending"
    sentiment: str | None = None
    duration: int = 0
    latency_ms: int | None = None
    twilio_call_sid: str | None = None
    provider_error: str | None = None
    provider_error_code: str | None = None
    created_at: datetime
    updated_at: datetime
