from dataclasses import dataclass
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.twiml.voice_response import Connect, VoiceResponse
from app.core.config import Settings
from app.core.logger import logger


@dataclass
class CallStartResult:
    """Normalized result so routes do not need to understand Twilio exceptions."""
    provider_call_id: str | None = None
    error: str | None = None
    error_code: str | None = None

    @property
    def ok(self) -> bool:
        """A call is considered started when Twilio returned a provider id."""
        return self.provider_call_id is not None


class TwilioService:
    def __init__(self, settings: Settings):
        """Create a Twilio client only when credentials are configured."""
        self.settings = settings
        self.client = (
            Client(settings.twilio_account_sid, settings.twilio_auth_token)
            if settings.twilio_account_sid and settings.twilio_auth_token
            else None
        )

    def media_stream_twiml(self, call_id: str, system_type: str) -> str:
        """Build TwiML that connects Twilio call audio to our media WebSocket."""
        response = VoiceResponse()
        connect = Connect()
        connect.stream(url=f"{self.settings.public_webhook_base_url}/ws/twilio/{call_id}/{system_type}")
        response.append(connect)
        return str(response)

    async def start_outbound_call(self, phone_number: str, call_id: str, system_type: str) -> CallStartResult:
        """Ask Twilio to dial the patient and call back to our TwiML endpoint."""
        if not self.client or not self.settings.public_webhook_base_url:
            message = "Twilio outbound call skipped because credentials or PUBLIC_WEBHOOK_BASE_URL are missing"
            logger.warning(message)
            return CallStartResult(error=message)
        try:
            call = self.client.calls.create(
                to=phone_number,
                from_=self.settings.twilio_phone_number,
                url=f"{self.settings.public_webhook_base_url}/calls/{call_id}/twiml?system_type={system_type}",
                method="POST",
            )
            return CallStartResult(provider_call_id=call.sid)
        except TwilioRestException as exc:
            logger.warning("Twilio outbound call failed: %s", exc)
            return CallStartResult(error=str(exc), error_code=str(exc.code) if exc.code else None)
