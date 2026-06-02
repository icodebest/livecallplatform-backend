import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"pbkdf2_sha256${salt}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt, encoded = stored.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return hmac.compare_digest(base64.b64encode(digest).decode(), encoded)


def create_token(payload: dict, secret: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    body = payload | {"iat": int(now.timestamp()), "exp": int((now + expires_delta).timestamp())}
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = f"{_b64_json(header)}.{_b64_json(body)}"
    signature = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}"


def decode_token(token: str, secret: str) -> dict:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}"
        expected = _b64(hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, signature_b64):
            raise ValueError("Invalid signature")
        payload = json.loads(_b64_decode(payload_b64))
        if datetime.now(timezone.utc).timestamp() > payload.get("exp", 0):
            raise ValueError("Token expired")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _b64_json(value: dict) -> str:
    return _b64(json.dumps(value, separators=(",", ":")).encode())


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _b64_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode())
