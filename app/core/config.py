from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables and .env."""
    app_name: str = "Maya Health Voice"
    environment: str = "development"
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    clinic_name: str = "CityCare Clinic"
    default_reschedule_slots: str = "Thursday 11:00 AM, Friday 4:00 PM"

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "health_voice_calls"

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4.1"
    openai_realtime_model: str = "gpt-4o-realtime-preview"
    openai_tts_voice: str = "alloy"

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    public_webhook_base_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Reuse one Settings object so every request sees the same configuration."""
    return Settings()
