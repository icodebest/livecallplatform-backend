import base64
import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.deps import get_user_from_token
from app.core.config import get_settings
from app.core.database import get_db
from app.core.logger import logger
from app.services.conversation_service import ConversationService
from app.services.openai_service import OpenAIService
from app.services.realtime_service import RealtimeService
from app.services.session_service import SessionService
from app.services.summary_service import SummaryService
from app.websocket.manager import manager

router = APIRouter()


@router.websocket("/ws/sessions/{session_id}/voice")
async def browser_voice_session(websocket: WebSocket, session_id: str, token: str):
    await websocket.accept()
    try:
        user = await get_user_from_token(token)
    except Exception:
        await websocket.send_json({"type": "error", "message": "Authentication failed"})
        await websocket.close(code=1008)
        return

    settings = get_settings()
    session_service = SessionService(get_db())
    openai_service = OpenAIService(settings)
    conversation = ConversationService(settings.clinic_name, settings.default_reschedule_slots)
    summary_service = SummaryService(openai_service)
    session = await session_service.get(session_id, user)
    if not session:
        await websocket.close(code=1008)
        return

    client_connected = True

    async def send_to_client(payload: dict) -> None:
        nonlocal client_connected
        if not client_connected:
            return
        try:
            await websocket.send_json(payload)
        except WebSocketDisconnect:
            client_connected = False
        except RuntimeError:
            client_connected = False

    async def publish(payload: dict):
        await send_to_client(payload)
        await manager.broadcast(f"session:{session_id}", payload)

    async def on_transcript(speaker: str, text: str):
        await session_service.append_transcript(session_id, user, speaker, text)
        await publish({"type": "transcript", "speaker": speaker, "text": text})

    async def on_status(payload: dict):
        await publish(payload)

    await session_service.start(session_id, user)
    await publish({"type": "status", "status": "in_progress", "system_type": session["system_type"]})
    started = time.perf_counter()
    try:
        if session["system_type"] == "realtime":
            realtime = RealtimeService(settings, conversation)
            await realtime.proxy_browser_to_openai(websocket, session, on_transcript, on_status)
        else:
            await run_modular_pipeline(websocket, session, user, session_service, openai_service, conversation, on_transcript, on_status)
    except WebSocketDisconnect:
        client_connected = False
    except Exception as exc:
        logger.exception("Voice session failed: %s", exc)
        await publish({"type": "error", "message": "Voice session failed. Please try again."})
    finally:
        latest = await session_service.get(session_id, user)
        summary = await summary_service.summarize(latest.get("transcript", []) if latest else [])
        completed = await session_service.complete(session_id, user, summary)
        duration = int(time.perf_counter() - started)
        await publish({"type": "duration", "duration": duration})
        await publish({"type": "completed", "session": completed})
        if client_connected:
            try:
                await websocket.close()
            except RuntimeError:
                pass


@router.websocket("/ws/sessions/{session_id}/monitor")
async def monitor_session(websocket: WebSocket, session_id: str, token: str):
    try:
        await get_user_from_token(token)
    except Exception:
        await websocket.close(code=1008)
        return
    channel = f"session:{session_id}"
    await manager.connect(channel, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(channel, websocket)


async def run_modular_pipeline(websocket, session, user, session_service, openai_service, conversation, on_transcript, on_status):
    if not session.get("transcript"):
        greeting = conversation.build_initial_message(session)
        await on_transcript("ai", greeting)
        speech = await openai_service.synthesize_speech(greeting)
        if speech:
            await websocket.send_json({"type": "audio", "audio": base64.b64encode(speech).decode(), "format": "mp3"})

    async for raw in websocket.iter_text():
        event = json.loads(raw)
        if event.get("type") == "stop":
            break
        if event.get("type") != "audio":
            continue
        started = time.perf_counter()
        audio = base64.b64decode(event["audio"])
        patient_text = await openai_service.transcribe_audio(audio, event.get("mime_type", "audio/webm"))
        if not patient_text:
            await on_status({"type": "notice", "message": "No clear speech detected."})
            continue
        await on_transcript("patient", patient_text)
        latest = await session_service.get(session["id"], user)
        reply, latency_ms = await openai_service.generate_reply(
            conversation.build_context(session),
            latest.get("transcript", []),
        )
        await session_service.record_latency(session["id"], user, latency_ms)
        await on_status({"type": "latency", "latency_ms": latency_ms, "active_speaker": "ai"})
        await on_transcript("ai", reply)
        speech = await openai_service.synthesize_speech(reply)
        if speech:
            await websocket.send_json({"type": "audio", "audio": base64.b64encode(speech).decode(), "format": "mp3"})
        await on_status({"type": "duration_tick", "elapsed_ms": int((time.perf_counter() - started) * 1000)})
