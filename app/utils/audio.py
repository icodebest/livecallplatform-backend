import base64


def decode_twilio_payload(payload: str) -> bytes:
    """Decode Twilio's base64 media payload into raw audio bytes."""
    return base64.b64decode(payload)


def encode_twilio_payload(audio: bytes) -> str:
    """Encode audio bytes into the base64 payload Twilio expects."""
    return base64.b64encode(audio).decode("utf-8")
