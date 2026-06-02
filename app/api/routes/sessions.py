from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.session_schema import SessionCreate
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


def get_session_service() -> SessionService:
    return SessionService(get_db())


@router.post("")
async def create_session(
    payload: SessionCreate,
    user: dict = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
):
    return await service.create(payload, user)


@router.get("")
async def list_sessions(user: dict = Depends(get_current_user), service: SessionService = Depends(get_session_service)):
    return await service.list(user)


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
):
    session = await service.get(session_id, user)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
