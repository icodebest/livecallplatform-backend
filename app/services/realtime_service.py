import json
import websockets
from websockets.exceptions import ConnectionClosedOK
from fastapi import WebSocket
from app.core.config import Settings
from app.core.logger import logger
from app.services.conversation_service import ConversationService, SYSTEM_PROMPT


class RealtimeService:
    def __init__(self, settings: Settings, conversation_service: ConversationService):
        """Keep realtime settings and prompt helpers together for the stream."""
        self.settings = settings
        self.conversation_service = conversation_service

    async def proxy_browser_to_openai(self, websocket: WebSocket, session: dict, on_transcript, on_status):
        """Open an OpenAI realtime socket and bridge browser PCM audio into it."""
        if not self.settings.openai_api_key:
            await websocket.send_json({"type": "error", "message": "OPENAI_API_KEY is not configured"})
            return

        url = f"wss://api.openai.com/v1/realtime?model={self.settings.openai_realtime_model}"
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
        }
        async with websockets.connect(url, additional_headers=headers) as openai_ws:
            await openai_ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "type": "realtime",
                    "model": self.settings.openai_realtime_model,
                    "instructions": f"{SYSTEM_PROMPT}\n\n{self.conversation_service.build_context(session)}",
                    "output_modalities": ["audio"],
                    "audio": {
                        "input": {
                            "format": {"type": "audio/pcm", "rate": 24000},
                            "transcription": {"model": "gpt-4o-mini-transcribe"},
                            "turn_detection": {
                                "type": "server_vad",
                                "threshold": 0.5,
                                "prefix_padding_ms": 300,
                                "silence_duration_ms": 600,
                            },
                        },
                        "output": {
                            "format": {"type": "audio/pcm", "rate": 24000},
                            "voice": self.settings.openai_tts_voice,
                        },
                    },
                },
            }))
            await openai_ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Start the session now with the initial appointment greeting."}],
                },
            }))
            await openai_ws.send(json.dumps({"type": "response.create"}))
            await self._bridge(websocket, openai_ws, on_transcript, on_status)

    async def _bridge(self, browser_ws: WebSocket, openai_ws, on_transcript, on_status):
        """Run both socket directions until either side disconnects or fails."""
        async def from_browser():
            """Forward browser PCM chunks into OpenAI."""
            async for raw in browser_ws.iter_text():
                event = json.loads(raw)
                if event.get("type") == "audio":
                    await openai_ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": event["audio"],
                    }))
                elif event.get("type") == "stop":
                    await openai_ws.close()
                    break

        async def from_openai():
            """Forward OpenAI audio and transcript events back to the browser."""
            async for raw in openai_ws:
                event = json.loads(raw)
                if event.get("type") in {"response.output_audio.delta", "response.audio.delta"}:
                    await browser_ws.send_json({"type": "audio", "audio": event.get("delta"), "format": "pcm16"})
                    await on_status({"type": "speaker", "active_speaker": "ai"})
                if event.get("type") in {
                    "conversation.item.input_audio_transcription.completed",
                    "response.output_audio_transcript.done",
                    "response.audio_transcript.done",
                }:
                    text = event.get("transcript") or event.get("text")
                    speaker = "patient" if "input_audio" in event.get("type", "") else "ai"
                    if text:
                        await on_transcript(speaker, text)
                if event.get("type") in {"input_audio_buffer.speech_started", "input_audio_buffer.speech_stopped"}:
                    await on_status({"type": "speaker", "active_speaker": "patient"})

        import asyncio
        tasks = [asyncio.create_task(from_browser()), asyncio.create_task(from_openai())]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in pending:
            task.cancel()
        for task in done:
            exc = task.exception()
            if isinstance(exc, ConnectionClosedOK):
                continue
            if exc:
                logger.exception("Realtime bridge failed", exc_info=task.exception())
