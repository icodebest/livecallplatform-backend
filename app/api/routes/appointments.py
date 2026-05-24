from fastapi import APIRouter, Depends, HTTPException
from app.core.database import get_db
from app.schemas.appointment_schema import AppointmentCreate, AppointmentUpdate
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments", tags=["appointments"])


def get_appointment_service() -> AppointmentService:
    """Build the appointment service around the active Mongo database."""
    return AppointmentService(get_db())


@router.get("")
async def list_appointments(status: str | None = None, service: AppointmentService = Depends(get_appointment_service)):
    """List appointments, optionally narrowed to one status."""
    return await service.list(status)


@router.post("")
async def create_appointment(payload: AppointmentCreate, service: AppointmentService = Depends(get_appointment_service)):
    """Create a scheduled appointment that can later be called or updated."""
    return await service.create(payload)


@router.patch("/{appointment_id}")
async def patch_appointment(
    appointment_id: str,
    payload: AppointmentUpdate,
    service: AppointmentService = Depends(get_appointment_service),
):
    """Apply partial appointment changes and return a 404 when the id is unknown."""
    appointment = await service.patch(appointment_id, payload)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment
