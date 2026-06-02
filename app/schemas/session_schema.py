from typing import Literal

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    patient_name: str = Field(min_length=1, max_length=120)
    doctor_name: str = Field(min_length=1, max_length=120)
    appointment_date: str = Field(min_length=1, max_length=40)
    appointment_time: str = Field(min_length=1, max_length=40)
    notes: str | None = None
    preferred_language: Literal["auto", "english", "urdu", "mixed"] = "auto"
    appointment_id: str | None = None
    system_type: Literal["realtime", "modular"] = "realtime"
