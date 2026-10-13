from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.register_patient(payload, ip_address=get_client_ip(request))
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.authenticate(payload.email, payload.password, ip_address=get_client_ip(request))
    access_token, refresh_token = service.issue_tokens(user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    access_token = service.refresh_access_token(payload.refresh_token)
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    service.revoke_refresh_token(payload.refresh_token)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    service.change_password(
        current_user, payload.current_password, payload.new_password, ip_address=get_client_ip(request)
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    token = service.request_password_reset(payload.email, ip_address=get_client_ip(request))
    # Em produção o token seria enviado por e-mail; aqui é retornado para fins de teste/demonstração.
    return ForgotPasswordResponse(
        message="Se o e-mail existir em nossa base, um token de recuperação foi gerado.",
        reset_token=token,
    )


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    service.reset_password(payload.token, payload.new_password, ip_address=get_client_ip(request))


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user
