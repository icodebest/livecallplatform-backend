from fastapi import APIRouter, Depends, HTTPException, Response
from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.call_schema import OutboundCallRequest
from app.services.call_service import CallService
from app.services.twilio_service import TwilioService

router = APIRouter(prefix="/calls", tags=["calls"])


def get_call_service() -> CallService:
    """Build the call service with the current database and Twilio settings."""
    return CallService(get_db(), TwilioService(get_settings()))


@router.post("/outbound")
async def outbound_call(payload: OutboundCallRequest, service: CallService = Depends(get_call_service)):
    """Create a call record, then ask Twilio to start dialing the patient."""
    return await service.create_outbound(payload)


@router.get("")
async def list_calls(service: CallService = Depends(get_call_service)):
    """Return recent calls for the call history screen."""
    return await service.list()


@router.get("/{call_id}")
async def get_call(call_id: str, service: CallService = Depends(get_call_service)):
    """Return one call with its transcript, summary, provider data, and metrics."""
    call = await service.get(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.post("/{call_id}/twiml")
async def call_twiml(call_id: str, system_type: str, service: CallService = Depends(get_call_service)):
    """Give Twilio XML that tells the call to stream audio into our WebSocket."""
    twiml = service.twilio_service.media_stream_twiml(call_id, system_type)
    return Response(content=twiml, media_type="application/xml")
