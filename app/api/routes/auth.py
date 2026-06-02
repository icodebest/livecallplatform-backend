from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.auth_schema import ForgotPasswordRequest, LoginRequest, ResetPasswordRequest, SignupRequest, VerifyEmailRequest
from app.services.auth_service import AuthService, _public_user

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service() -> AuthService:
    return AuthService(get_db(), get_settings())


@router.post("/signup")
async def signup(payload: SignupRequest, service: AuthService = Depends(get_auth_service)):
    return await service.signup(payload)


@router.post("/verify")
async def verify_email(payload: VerifyEmailRequest, service: AuthService = Depends(get_auth_service)):
    return await service.verify_email(payload)


@router.post("/login")
async def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)):
    return await service.login(payload)


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, service: AuthService = Depends(get_auth_service)):
    return await service.forgot_password(payload)


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, service: AuthService = Depends(get_auth_service)):
    return await service.reset_password(payload)


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return _public_user(user)
