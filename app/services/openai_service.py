import json
import time
from openai import AsyncOpenAI
from app.core.config import Settings
from app.services.conversation_service import SYSTEM_PROMPT


class OpenAIService:
    def __init__(self, settings: Settings):
        """Create the async OpenAI client when an API key is available."""
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """Turn patient audio into text for the modular voice pipeline."""
        if not self.client:
            return ""
        # Production note: convert Twilio mulaw/8k audio into a supported input format before this call.
        result = await self.client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=("speech.wav", audio_bytes, "audio/wav"),
        )
        return result.text

    async def generate_reply(self, context: str, transcript: list[dict]) -> tuple[str, int]:
        """Ask the chat model for the next assistant response and measure latency."""
        if not self.client:
            return "I am unable to reach the AI service right now. A clinic team member will follow up.", 0

        start = time.perf_counter()
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "system", "content": context}]
        for turn in transcript[-12:]:
            role = "assistant" if turn["speaker"] == "ai" else "user"
            messages.append({"role": role, "content": turn["text"]})
        response = await self.client.chat.completions.create(
            model=self.settings.openai_chat_model,
            messages=messages,
            temperature=0.4,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        return response.choices[0].message.content or "", latency_ms

    async def synthesize_speech(self, text: str) -> bytes:
        """Convert assistant text into speech bytes for Twilio playback."""
        if not self.client:
            return b""
        response = await self.client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=self.settings.openai_tts_voice,
            input=text,
            response_format="wav",
        )
        return response.read()

    async def summarize_call(self, transcript: list[dict]) -> dict:
        """Summarize the finished transcript into outcome, sentiment, and notes."""
        if not self.client or not transcript:
            return {"summary": "No transcript was captured.", "outcome": "failed", "sentiment": "unknown"}

        response = await self.client.chat.completions.create(
            model=self.settings.openai_chat_model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Summarize the healthcare appointment call as JSON with keys: "
                        "summary, outcome, sentiment, appointment_update. Outcome must be one of "
                        "confirmed, rescheduled, cancelled, failed, voicemail, escalated, pending."
                    ),
                },
                {"role": "user", "content": json.dumps(transcript, default=str)},
            ],
            temperature=0.1,
        )
        return json.loads(response.choices[0].message.content or "{}")
