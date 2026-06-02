from bson import ObjectId
from fastapi import Depends, Header, HTTPException, status

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import decode_token
from app.services.auth_service import AuthService


async def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token, get_settings().jwt_secret)
    user = await get_db().users.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    auth_service = AuthService(get_db(), get_settings())
    auth_service.ensure_trial_active(user)
    return user


async def get_user_from_token(token: str) -> dict:
    payload = decode_token(token, get_settings().jwt_secret)
    user = await get_db().users.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    AuthService(get_db(), get_settings()).ensure_trial_active(user)
    return user
