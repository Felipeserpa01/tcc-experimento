from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth_service import AuthService
from app.core.security import decode_token
from app.core.exceptions import AppException, UnauthorizedError
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenPair, RefreshRequest,
    PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirm, UserRead
)
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User:
    if not authorization:
        raise UnauthorizedError("Missing authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise UnauthorizedError("Invalid authorization scheme")
    except ValueError:
        raise UnauthorizedError("Invalid authorization header format")

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedError("Invalid or expired token")

    user_id = int(payload.get("sub"))
    from app.repositories.user_repository import UserRepository
    user_repo = UserRepository(db)
    user = user_repo.get(user_id)

    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return user


@router.post("/register", response_model=UserRead)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    try:
        auth_service = AuthService(db)
        user = auth_service.register(request.email, request.password, request.full_name)
        return user
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/login", response_model=dict)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    try:
        auth_service = AuthService(db)
        result = auth_service.login(request.email, request.password)
        return result
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/refresh", response_model=dict)
async def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    try:
        auth_service = AuthService(db)
        result = auth_service.refresh_access_token(request.refresh_token)
        return result
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        auth_service = AuthService(db)
        auth_service.logout(current_user.id)
        return {"message": "Logged out successfully"}
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        auth_service = AuthService(db)
        auth_service.change_password(current_user.id, request.old_password, request.new_password)
        return {"message": "Password changed successfully"}
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/password-reset/request")
async def request_password_reset(request: PasswordResetRequest, db: Session = Depends(get_db)):
    try:
        auth_service = AuthService(db)
        token = auth_service.request_password_reset(request.email)
        return {
            "message": "If email exists, a reset token will be sent",
            "reset_token": token  # Demo only - remove before production
        }
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/password-reset/confirm")
async def confirm_password_reset(request: PasswordResetConfirm, db: Session = Depends(get_db)):
    try:
        auth_service = AuthService(db)
        auth_service.confirm_password_reset(request.token, request.new_password)
        return {"message": "Password reset successfully"}
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
