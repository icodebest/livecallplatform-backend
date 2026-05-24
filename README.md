# Backend

FastAPI service for AI appointment calling, MongoDB persistence, Twilio Voice webhooks, and OpenAI-powered conversation handling.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Run commands from the `backend/` directory.

## Key Routes

- `POST /calls/outbound` starts an outbound appointment call.
- `GET /calls` lists call records.
- `GET /calls/{id}` returns transcript, summary, outcome, and metrics.
- `POST /calls/{id}/twiml` returns Twilio Media Stream TwiML.
- `GET /appointments` lists appointments.
- `PATCH /appointments/{id}` updates appointment status or details.
- `GET /dashboard/stats` returns dashboard metrics.
- `WS /ws/twilio/{call_id}/{system_type}` receives Twilio media streams.
- `WS /ws/calls/{call_id}/monitor` streams live transcript events to the UI.

## Telephony Notes

Twilio trial accounts can reject real outbound calls even when the code path is correct. For example, error `21219` means the destination number is not verified for a trial account. The backend records those provider failures on the call document as `provider_error` and marks the call as `failed` instead of leaving it in a misleading pending state.

## Architecture

The backend supports two AI systems selected per call:

- Realtime: Twilio Media Streams are proxied to OpenAI Realtime API for low-latency speech-to-speech conversation and interruption handling.
- Modular: Twilio audio is processed through STT, GPT conversation, TTS, and streamed back to Twilio for observability and component-level control.

Business logic lives in `app/services`, REST routes stay thin, and MongoDB access uses Motor async APIs.
