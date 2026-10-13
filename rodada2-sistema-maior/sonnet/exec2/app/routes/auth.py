"""Authentication endpoints."""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.exceptions import ValidationAppError
from app.database import get_db
from app.dependencies import get_client_ip, get_current_user
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, request: Request, db: Session = Depends(get_db)):
    if payload.role != UserRole.PACIENTE:
        raise ValidationAppError(
            "O autorregistro público é permitido apenas para pacientes. "
            "Contas de equipe são criadas por um administrador."
        )
    service = AuthService(db)
    user = service.register(payload, ip_address=get_client_ip(request))
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.authenticate(payload.email, payload.password, ip_address=get_client_ip(request))
    access, refresh = service.issue_tokens(user)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    access = service.refresh_access_token(payload.refresh_token)
    return AccessTokenResponse(access_token=access)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    service.change_password(
        current_user, payload.current_password, payload.new_password, ip_address=get_client_ip(request)
    )
    return MessageResponse(message="Senha alterada com sucesso.")


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    # The plain token would be emailed to the user in production; it is intentionally
    # not returned here to avoid leaking a takeover credential through the API response.
    service.request_password_reset(payload.email, ip_address=get_client_ip(request))
    return MessageResponse(
        message="Se o e-mail informado estiver cadastrado, instruções de recuperação foram enviadas."
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: PasswordResetConfirm, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    service.confirm_password_reset(payload.token, payload.new_password, ip_address=get_client_ip(request))
    return MessageResponse(message="Senha redefinida com sucesso.")
