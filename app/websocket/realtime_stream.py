from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket.manager import manager

router = APIRouter()


@router.websocket("/ws/calls/{call_id}/monitor")
async def monitor_call(websocket: WebSocket, call_id: str):
    """Let the frontend subscribe to live transcript and completion events."""
    channel = f"call:{call_id}"
    await manager.connect(channel, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(channel, websocket)
