"""Rotas de autenticacao e seguranca da conta."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.repositories.patient_repository import PatientRepository
from app.repositories.professional_repository import ProfessionalRepository
from app.schemas.auth import (
    AuthenticatedUser,
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    PasswordRecoveryRequest,
    PasswordRecoveryResponse,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticacao"])
settings = get_settings()


def _build_profile(db: Session, user: User) -> AuthenticatedUser:
    patient = PatientRepository(db).get_by_user_id(user.id)
    professional = ProfessionalRepository(db).get_by_user_id(user.id)
    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        patient_id=patient.id if patient else None,
        professional_id=professional.id if professional else None,
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Auto cadastro de paciente",
    description=(
        "Cria um usuario com perfil `patient` e o cadastro basico do paciente. "
        "Perfis internos (admin, medico, enfermeiro, recepcionista) sao criados em `/users`."
    ),
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserRead:
    user = AuthService(db).register_patient(payload)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse, summary="Login com email e senha")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    _, access_token, refresh_token, expires_in = AuthService(db).authenticate(
        payload.email, payload.password
    )
    return TokenResponse(
        access_token=access_token, refresh_token=refresh_token, expires_in=expires_in
    )


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Login compativel com OAuth2 (usado pelo Swagger)",
    include_in_schema=True,
)
def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> TokenResponse:
    _, access_token, refresh_token, expires_in = AuthService(db).authenticate(
        form_data.username, form_data.password
    )
    return TokenResponse(
        access_token=access_token, refresh_token=refresh_token, expires_in=expires_in
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renova o access token (com rotacao do refresh token)",
)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    _, access_token, refresh_token, expires_in = AuthService(db).refresh_session(
        payload.refresh_token
    )
    return TokenResponse(
        access_token=access_token, refresh_token=refresh_token, expires_in=expires_in
    )


@router.post("/logout", response_model=MessageResponse, summary="Encerra a sessao")
def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    revoked = AuthService(db).logout(current_user, payload.refresh_token, payload.all_sessions)
    return MessageResponse(
        message="Sessao encerrada com sucesso.", detail={"revoked_sessions": revoked}
    )


@router.get("/me", response_model=AuthenticatedUser, summary="Dados do usuario autenticado")
def me(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> AuthenticatedUser:
    return _build_profile(db, current_user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Troca de senha pelo proprio usuario",
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    AuthService(db).change_password(
        current_user, payload.current_password, payload.new_password
    )
    return MessageResponse(
        message="Senha alterada com sucesso. Faca login novamente para obter novos tokens."
    )


@router.post(
    "/password-recovery",
    response_model=PasswordRecoveryResponse,
    summary="Solicita token de recuperacao de senha",
    description=(
        "A resposta e sempre a mesma, exista ou nao o email informado, para nao revelar "
        "quais emails estao cadastrados. Fora de producao o token e devolvido no corpo "
        "para facilitar testes."
    ),
)
def password_recovery(
    payload: PasswordRecoveryRequest, db: Session = Depends(get_db)
) -> PasswordRecoveryResponse:
    raw_token, reset = AuthService(db).request_password_recovery(payload.email)
    expose_token = raw_token if (raw_token and not settings.is_production) else None
    return PasswordRecoveryResponse(
        message=(
            "Se o email estiver cadastrado, enviaremos as instrucoes de recuperacao de senha."
        ),
        reset_token=expose_token,
        expires_at=reset.expires_at if (reset and not settings.is_production) else None,
    )


@router.post(
    "/password-reset",
    response_model=MessageResponse,
    summary="Redefine a senha usando o token de recuperacao",
)
def password_reset(
    payload: PasswordResetRequest, db: Session = Depends(get_db)
) -> MessageResponse:
    AuthService(db).reset_password(payload.token, payload.new_password)
    return MessageResponse(message="Senha redefinida com sucesso.")
