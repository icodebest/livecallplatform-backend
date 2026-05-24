import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.config import get_settings
from app.core.database import get_db
from app.services.call_service import CallService
from app.services.conversation_service import ConversationService
from app.services.openai_service import OpenAIService
from app.services.realtime_service import RealtimeService
from app.services.summary_service import SummaryService
from app.services.twilio_service import TwilioService
from app.utils.audio import decode_twilio_payload, encode_twilio_payload
from app.websocket.manager import manager

router = APIRouter()


@router.websocket("/ws/twilio/{call_id}/{system_type}")
async def twilio_media_stream(websocket: WebSocket, call_id: str, system_type: str):
    """Receive Twilio Media Stream events and run the selected AI call pipeline."""
    await websocket.accept()
    settings = get_settings()
    db = get_db()
    conversation = ConversationService(settings.clinic_name, settings.default_reschedule_slots)
    openai_service = OpenAIService(settings)
    call_service = CallService(db, TwilioService(settings))
    summary_service = SummaryService(openai_service)
    call = await call_service.get(call_id)
    if not call:
        await websocket.close(code=1008)
        return

    async def on_transcript(speaker: str, text: str):
        """Persist each spoken turn and push it to live dashboard listeners."""
        await call_service.append_transcript(call_id, speaker, text)
        await manager.broadcast(f"call:{call_id}", {"type": "transcript", "speaker": speaker, "text": text})

    try:
        if system_type == "realtime":
            realtime = RealtimeService(settings, conversation)
            await realtime.proxy_twilio_to_openai(websocket, call, on_transcript)
        else:
            await run_modular_pipeline(websocket, call, call_service, openai_service, conversation, on_transcript)
    except WebSocketDisconnect:
        pass
    finally:
        latest = await call_service.get(call_id)
        summary = await summary_service.summarize(latest.get("transcript", []) if latest else [])
        completed = await call_service.complete(call_id, summary)
        await manager.broadcast(f"call:{call_id}", {"type": "completed", "call": completed})


async def run_modular_pipeline(websocket: WebSocket, call: dict, call_service, openai_service, conversation, on_transcript):
    """Handle the STT -> chat -> TTS loop for the modular voice system."""
    await on_transcript("ai", conversation.build_initial_message(call))
    async for raw in websocket.iter_text():
        event = json.loads(raw)
        if event.get("event") != "media":
            continue
        audio = decode_twilio_payload(event["media"]["payload"])
        patient_text = await openai_service.transcribe_audio(audio)
        if not patient_text:
            continue
        await on_transcript("patient", patient_text)
        latest = await call_service.get(call["id"])
        reply, latency_ms = await openai_service.generate_reply(
            conversation.build_context(call),
            latest.get("transcript", []),
        )
        await on_transcript("ai", reply)
        speech = await openai_service.synthesize_speech(reply)
        if speech:
            await websocket.send_json({"event": "media", "media": {"payload": encode_twilio_payload(speech)}})
        await manager.broadcast(
            f"call:{call['id']}",
            {"type": "latency", "latency_ms": latency_ms, "active_speaker": "ai"},
        )
