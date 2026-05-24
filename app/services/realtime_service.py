import json
import websockets
from fastapi import WebSocket
from app.core.config import Settings
from app.core.logger import logger
from app.services.conversation_service import ConversationService, SYSTEM_PROMPT


class RealtimeService:
    def __init__(self, settings: Settings, conversation_service: ConversationService):
        """Keep realtime settings and prompt helpers together for the stream."""
        self.settings = settings
        self.conversation_service = conversation_service

    async def proxy_twilio_to_openai(self, websocket: WebSocket, call: dict, on_transcript):
        """Open an OpenAI realtime socket and bridge Twilio audio into it."""
        if not self.settings.openai_api_key:
            await websocket.send_json({"event": "error", "message": "OPENAI_API_KEY is not configured"})
            return

        url = f"wss://api.openai.com/v1/realtime?model={self.settings.openai_realtime_model}"
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "OpenAI-Beta": "realtime=v1",
        }
        async with websockets.connect(url, additional_headers=headers) as openai_ws:
            await openai_ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "instructions": f"{SYSTEM_PROMPT}\n\n{self.conversation_service.build_context(call)}",
                    "voice": self.settings.openai_tts_voice,
                    "input_audio_format": "g711_ulaw",
                    "output_audio_format": "g711_ulaw",
                    "turn_detection": {"type": "server_vad"},
                },
            }))
            await self._bridge(websocket, openai_ws, on_transcript)

    async def _bridge(self, twilio_ws: WebSocket, openai_ws, on_transcript):
        """Run both socket directions until either side disconnects or fails."""
        async def from_twilio():
            """Forward patient audio chunks from Twilio into OpenAI."""
            async for raw in twilio_ws.iter_text():
                event = json.loads(raw)
                if event.get("event") == "media":
                    await openai_ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": event["media"]["payload"],
                    }))

        async def from_openai():
            """Forward OpenAI audio back to Twilio and save transcript events."""
            async for raw in openai_ws:
                event = json.loads(raw)
                if event.get("type") == "response.audio.delta":
                    await twilio_ws.send_json({
                        "event": "media",
                        "media": {"payload": event.get("delta")},
                    })
                if event.get("type") in {"conversation.item.input_audio_transcription.completed", "response.audio_transcript.done"}:
                    text = event.get("transcript") or event.get("text")
                    speaker = "patient" if "input_audio" in event.get("type", "") else "ai"
                    if text:
                        await on_transcript(speaker, text)

        import asyncio
        tasks = [asyncio.create_task(from_twilio()), asyncio.create_task(from_openai())]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in pending:
            task.cancel()
        for task in done:
            if task.exception():
                logger.exception("Realtime bridge failed", exc_info=task.exception())
