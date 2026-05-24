from typing import Literal
from pydantic import BaseModel, Field
from datetime import datetime


AppointmentStatus = Literal["scheduled", "confirmed", "rescheduled", "cancelled", "failed"]


class AppointmentModel(BaseModel):
    """Stored Mongo shape for a clinic appointment."""
    patient_name: str
    phone_number: str
    doctor_name: str
    appointment_date: str
    appointment_time: str
    status: AppointmentStatus = "scheduled"
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
