from app.services.openai_service import OpenAIService


class SummaryService:
    def __init__(self, openai_service: OpenAIService):
        """Wrap OpenAI summarization so callers get consistent response keys."""
        self.openai_service = openai_service

    async def summarize(self, transcript: list[dict]) -> dict:
        """Normalize model output into the fields stored on a completed call."""
        summary = await self.openai_service.summarize_call(transcript)
        return {
            "summary": summary.get("summary", "Summary unavailable."),
            "outcome": summary.get("outcome", "pending"),
            "sentiment": summary.get("sentiment", "unknown"),
            "appointment_update": summary.get("appointment_update", {}),
        }
