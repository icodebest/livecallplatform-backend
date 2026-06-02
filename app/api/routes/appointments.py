from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.appointment_schema import AppointmentCreate, AppointmentUpdate
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments", tags=["appointments"])


def get_appointment_service() -> AppointmentService:
    """Build the appointment service around the active Mongo database."""
    return AppointmentService(get_db())


@router.get("")
async def list_appointments(
    status: str | None = None,
    user: dict = Depends(get_current_user),
    service: AppointmentService = Depends(get_appointment_service),
):
    """List appointments, optionally narrowed to one status."""
    return await service.list(user, status)


@router.post("")
async def create_appointment(
    payload: AppointmentCreate,
    user: dict = Depends(get_current_user),
    service: AppointmentService = Depends(get_appointment_service),
):
    """Create a scheduled appointment that can later be used in a voice session."""
    return await service.create(payload, user)


@router.patch("/{appointment_id}")
async def patch_appointment(
    appointment_id: str,
    payload: AppointmentUpdate,
    user: dict = Depends(get_current_user),
    service: AppointmentService = Depends(get_appointment_service),
):
    """Apply partial appointment changes and return a 404 when the id is unknown."""
    appointment = await service.patch(appointment_id, payload, user)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment
