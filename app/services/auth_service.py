from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings
from app.core.security import create_token, generate_otp, hash_password, verify_password
from app.services.email_service import EmailService
from app.utils.helpers import now_utc, serialize_doc


class AuthService:
    def __init__(self, db: AsyncIOMotorDatabase, settings: Settings):
        self.collection = db.users
        self.settings = settings
        self.email_service = EmailService(settings)

    async def signup(self, payload) -> dict:
        existing = await self.collection.find_one({"email": payload.email.lower()})
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        otp = generate_otp()
        now = now_utc()
        doc = {
            "name": payload.name,
            "email": payload.email.lower(),
            "password_hash": hash_password(payload.password),
            "is_verified": False,
            "verification_otp": otp,
            "verification_expires_at": now + timedelta(minutes=15),
            "plan": None,
            "trial_started_at": None,
            "trial_expires_at": None,
            "created_at": now,
            "updated_at": now,
        }
        await self.collection.insert_one(doc)
        await self.email_service.send_verification_otp(payload.email.lower(), otp)
        return {"message": "Verification code sent"}

    async def verify_email(self, payload) -> dict:
        user = await self.collection.find_one({"email": payload.email.lower()})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.get("is_verified"):
            user = await self._ensure_trial_started(user)
            return self._auth_response(user)
        if user.get("verification_otp") != payload.otp:
            raise HTTPException(status_code=400, detail="Invalid verification code")
        if now_utc() > _as_utc(user.get("verification_expires_at")):
            raise HTTPException(status_code=400, detail="Verification code expired")

        now = now_utc()
        trial_expires_at = now + timedelta(hours=4)
        await self.collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "is_verified": True,
                    "verification_otp": None,
                    "verification_expires_at": None,
                    "trial_started_at": now,
                    "trial_expires_at": trial_expires_at,
                    "plan": "demo",
                    "updated_at": now,
                }
            },
        )
        verified = await self.collection.find_one({"_id": user["_id"]})
        return self._auth_response(verified)

    async def login(self, payload) -> dict:
        user = await self.collection.find_one({"email": payload.email.lower()})
        if not user or not verify_password(payload.password, user.get("password_hash", "")):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        if not user.get("is_verified"):
            raise HTTPException(status_code=403, detail="Email verification required")
        user = await self._ensure_trial_started(user)
        self.ensure_trial_active(user)
        return self._auth_response(user)

    async def forgot_password(self, payload) -> dict:
        user = await self.collection.find_one({"email": payload.email.lower()})
        if user:
            otp = generate_otp()
            await self.collection.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "password_reset_otp": otp,
                        "password_reset_expires_at": now_utc() + timedelta(minutes=15),
                        "updated_at": now_utc(),
                    }
                },
            )
            await self.email_service.send_password_reset_otp(user["email"], otp)
        return {"message": "If an account exists, a password reset code has been sent"}

    async def reset_password(self, payload) -> dict:
        user = await self.collection.find_one({"email": payload.email.lower()})
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired reset code")
        if user.get("password_reset_otp") != payload.otp:
            raise HTTPException(status_code=400, detail="Invalid or expired reset code")
        if now_utc() > _as_utc(user.get("password_reset_expires_at")):
            raise HTTPException(status_code=400, detail="Invalid or expired reset code")
        await self.collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "password_hash": hash_password(payload.password),
                    "password_reset_otp": None,
                    "password_reset_expires_at": None,
                    "updated_at": now_utc(),
                }
            },
        )
        return {"message": "Password reset successful"}

    async def _ensure_trial_started(self, user: dict) -> dict:
        if user.get("trial_started_at") and user.get("trial_expires_at") and user.get("plan"):
            return user
        now = now_utc()
        await self.collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "trial_started_at": now,
                    "trial_expires_at": now + timedelta(hours=4),
                    "plan": "demo",
                    "updated_at": now,
                }
            },
        )
        return await self.collection.find_one({"_id": user["_id"]})

    def ensure_trial_active(self, user: dict) -> None:
        expires_at = user.get("trial_expires_at")
        if not expires_at:
            raise HTTPException(status_code=403, detail="Demo trial not activated")
        if now_utc() > _as_utc(expires_at):
            raise HTTPException(status_code=403, detail="Demo trial expired")

    def _auth_response(self, user: dict) -> dict:
        self.ensure_trial_active(user)
        remaining = _as_utc(user["trial_expires_at"]) - now_utc()
        token_lifetime = min(timedelta(hours=8), remaining)
        token = create_token({"sub": str(user["_id"]), "email": user["email"]}, self.settings.jwt_secret, token_lifetime)
        return {"access_token": token, "token_type": "bearer", "user": _public_user(user)}


def _public_user(user: dict) -> dict:
    data = serialize_doc(user)
    for key in ("password_hash", "verification_otp", "verification_expires_at", "password_reset_otp", "password_reset_expires_at"):
        data.pop(key, None)
    return data


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
