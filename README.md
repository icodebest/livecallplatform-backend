# LiveCallPlatform Backend

FastAPI backend for an AI-powered healthcare calling platform. It manages appointment records, places outbound calls through Twilio, streams live call audio, coordinates OpenAI voice intelligence, stores transcripts and summaries in MongoDB, and exposes the data needed by the operations dashboard.

![Backend architecture](docs/images/backend-architecture.png)

> Add your backend architecture image at `docs/images/backend-architecture.png`.

## What This Service Does

- Starts outbound appointment calls through Twilio Voice.
- Receives Twilio Media Streams over WebSocket.
- Supports two AI call engines: OpenAI Realtime and a modular STT -> LLM -> TTS pipeline.
- Saves call lifecycle events, transcripts, summaries, outcomes, and latency metrics.
- Manages appointment status changes such as confirmed, rescheduled, cancelled, failed, and pending.
- Streams live transcript updates to the frontend monitoring view.

## Architecture

The backend is designed as a clean voice-orchestration layer between the clinic dashboard, Twilio, OpenAI, and MongoDB.

At the edge, FastAPI exposes REST endpoints for the dashboard and WebSocket endpoints for real-time audio and monitoring. When a user creates an outbound call, the API creates a call record in MongoDB, asks Twilio to dial the patient, and gives Twilio TwiML that connects the phone call to the backend media stream. From there, the selected AI system handles the conversation and continuously updates the stored call document.

The service supports two voice paths:

- **Realtime AI path**: Twilio streams audio to the backend, and the backend bridges that stream to OpenAI Realtime for low-latency speech-to-speech conversation, interruption handling, and natural turn-taking.
- **Modular AI path**: Twilio audio is processed through separate transcription, chat completion, and text-to-speech steps. This path is easier to observe, debug, and tune at each stage of the conversation pipeline.

Core business behavior lives in `app/services`, while API route files stay intentionally thin. MongoDB access uses Motor async APIs, and WebSocket handling is separated into dedicated modules under `app/websocket`.

## Call Flow Diagrams

### Realtime AI Call Flow

The realtime path is optimized for natural speech-to-speech conversation. Twilio streams the live phone audio into the backend, the backend bridges it to OpenAI Realtime, and call updates are saved to MongoDB while the dashboard receives live monitoring events.

![Realtime AI call flow](docs/images/realtime-call-flow.png)

> Add your realtime flow image at `docs/images/realtime-call-flow.png`.

### Modular AI Call Flow

The modular path separates the voice pipeline into observable steps: speech-to-text, conversation generation, and text-to-speech. This makes each stage easier to debug, tune, and measure.

![Modular AI call flow](docs/images/modular-call-flow.png)

> Add your modular flow image at `docs/images/modular-call-flow.png`.

## AI Models

- **Realtime voice**: `gpt-4o-realtime-preview`
- **Speech-to-text**: `gpt-4o-mini-transcribe`
- **Conversation LLM**: `gpt-4.1`
- **Text-to-speech**: `gpt-4o-mini-tts`
- **TTS voice**: `alloy`

## Tech Stack

- FastAPI
- Python async services
- MongoDB with Motor
- Twilio Voice and Media Streams
- OpenAI chat, transcription, text-to-speech, and realtime voice APIs
- WebSockets for live audio and dashboard monitoring

## Setup

Run these commands from the `backend/` directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `.env` with your real credentials:

```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=health_voice_calls

OPENAI_API_KEY=your-openai-api-key
OPENAI_CHAT_MODEL=gpt-4.1
OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview
OPENAI_TTS_VOICE=alloy

TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+15550000000
PUBLIC_WEBHOOK_BASE_URL=https://your-public-domain-or-ngrok-url
```

Start the API:

```bash
uvicorn app.main:app --reload
```

The backend runs at:

```text
http://localhost:8000
```

## Twilio Setup

1. Create or log in to your Twilio account.
2. Buy or select a Twilio phone number with Voice capability.
3. Copy your **Account SID**, **Auth Token**, and Twilio phone number into `.env`.
4. Expose your local backend with a public HTTPS URL while developing:

```bash
ngrok http 8000
```

5. Copy the HTTPS forwarding URL into `.env`:

```env
PUBLIC_WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok-free.app
```

6. Make sure your outbound call request uses a reachable patient phone number in E.164 format:

```text
+15551234567
```

7. When a call starts, the backend gives Twilio a TwiML response that opens a Media Stream WebSocket to:

```text
wss://your-public-domain/ws/twilio/{call_id}/{system_type}
```

8. For production, use a stable HTTPS domain instead of a temporary ngrok URL.

## Key Routes

- `POST /calls/outbound` starts an outbound appointment call.
- `GET /calls` lists call records.
- `GET /calls/{id}` returns transcript, summary, outcome, provider data, and metrics.
- `POST /calls/{id}/twiml` returns Twilio Media Stream TwiML.
- `GET /appointments` lists appointments.
- `POST /appointments` creates an appointment.
- `PATCH /appointments/{id}` updates appointment status or details.
- `GET /dashboard/stats` returns dashboard metrics.
- `WS /ws/twilio/{call_id}/{system_type}` receives Twilio call audio.
- `WS /ws/calls/{call_id}/monitor` streams live transcript events to the UI.
