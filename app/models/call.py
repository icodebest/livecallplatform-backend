from typing import Literal
from pydantic import BaseModel, Field
from datetime import datetime


SystemType = Literal["realtime", "modular"]
SessionOutcome = Literal["pending", "confirmed", "rescheduled", "cancelled", "failed", "voicemail", "escalated"]


class TranscriptTurn(BaseModel):
    """One line of conversation captured during a browser voice session."""
    speaker: Literal["ai", "patient", "system"]
    text: str
    timestamp: datetime


class SessionModel(BaseModel):
    """Stored Mongo shape for a browser-native appointment voice session."""
    patient_name: str
    doctor_name: str | None = None
    appointment_id: str | None = None
    system_type: SystemType
    status: Literal["created", "in_progress", "completed", "failed"] = "created"
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    summary: str = ""
    outcome: SessionOutcome = "pending"
    sentiment: str | None = None
    duration: int = 0
    latency_ms: int | None = None
    provider_error: str | None = None
    provider_error_code: str | None = None
    created_at: datetime
    updated_at: datetime
