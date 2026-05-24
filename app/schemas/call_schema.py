from typing import Literal
from pydantic import BaseModel, Field, field_validator


class OutboundCallRequest(BaseModel):
    """Request body the frontend sends when it wants to start a phone call."""
    patient_name: str = Field(min_length=1, max_length=120)
    phone_number: str = Field(min_length=8, max_length=20)
    doctor_name: str = Field(min_length=1, max_length=120)
    appointment_date: str = Field(min_length=1, max_length=40)
    appointment_time: str = Field(min_length=1, max_length=40)
    notes: str | None = None
    appointment_id: str | None = None
    system_type: Literal["realtime", "modular"] = "realtime"

    @field_validator("phone_number")
    @classmethod
    def phone_must_be_e164(cls, value: str) -> str:
        """Keep Twilio numbers in the international E.164 format."""
        if not value.startswith("+") or not value[1:].isdigit():
            raise ValueError("Phone number must use E.164 format, for example +921234567890")
        return value


class TranscriptTurnSchema(BaseModel):
    """API-safe transcript turn shape."""
    speaker: Literal["ai", "patient", "system"]
    text: str
    timestamp: str


class CallResponse(BaseModel):
    """Full call response shape returned to the frontend."""
    id: str
    patient_name: str
    phone_number: str
    doctor_name: str | None = None
    appointment_id: str | None = None
    system_type: str
    status: str
    transcript: list[dict] = Field(default_factory=list)
    summary: str = ""
    outcome: str
    sentiment: str | None = None
    duration: int = 0
    latency_ms: int | None = None
    twilio_call_sid: str | None = None
    provider_error: str | None = None
    provider_error_code: str | None = None
    created_at: str
    updated_at: str
