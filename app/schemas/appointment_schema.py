from typing import Literal
from pydantic import BaseModel


class AppointmentCreate(BaseModel):
    """Fields needed to create a new appointment."""
    patient_name: str
    phone_number: str
    doctor_name: str
    appointment_date: str
    appointment_time: str
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    """Optional fields allowed when editing an appointment."""
    patient_name: str | None = None
    phone_number: str | None = None
    doctor_name: str | None = None
    appointment_date: str | None = None
    appointment_time: str | None = None
    status: Literal["scheduled", "confirmed", "rescheduled", "cancelled", "failed"] | None = None
    notes: str | None = None


class AppointmentResponse(AppointmentCreate):
    """Appointment response shape after Mongo fields are serialized."""
    id: str
    status: str
    created_at: str
    updated_at: str
