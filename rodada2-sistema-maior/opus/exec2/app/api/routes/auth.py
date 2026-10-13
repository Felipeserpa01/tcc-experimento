from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import ERROR_RESPONSES, CurrentUser, get_auth_service
from app.schemas.auth import (
    ChangePasswordRequest,
    CurrentUserOut,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.common import ErrorResponse, MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticação"], responses=ERROR_RESPONSES)

Auth = Annotated[AuthService, Depends(get_auth_service)]


@router.post(
    "/register",
    response_model=CurrentUserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Autocadastro de paciente",
)
def register(data: RegisterRequest, auth: Auth) -> object:
    """Cria um usuário com perfil **paciente** e a respectiva ficha cadastral."""
    return auth.register_patient(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login (access + refresh token)",
    responses={423: {"model": ErrorResponse, "description": "Conta temporariamente bloqueada"}},
)
def login(data: LoginRequest, auth: Auth) -> TokenResponse:
    """Após 5 tentativas malsucedidas consecutivas, a conta é bloqueada temporariamente."""
    return auth.login(data.email, data.password)


@router.post("/refresh", response_model=TokenResponse, summary="Renovar tokens (rotação de refresh token)")
def refresh(data: RefreshRequest, auth: Auth) -> TokenResponse:
    return auth.refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Encerrar sessão (revoga o refresh token)")
def logout(data: RefreshRequest, user: CurrentUser, auth: Auth) -> None:
    auth.logout(user, data.refresh_token)


@router.get("/me", response_model=CurrentUserOut, summary="Dados do usuário autenticado")
def me(user: CurrentUser) -> object:
    return user


@router.post("/change-password", response_model=MessageResponse, summary="Trocar a própria senha")
def change_password(data: ChangePasswordRequest, user: CurrentUser, auth: Auth) -> MessageResponse:
    auth.change_password(user, data.current_password, data.new_password)
    return MessageResponse(message="Senha alterada com sucesso. Faça login novamente.")


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Solicitar recuperação de senha",
)
def forgot_password(data: ForgotPasswordRequest, auth: Auth) -> MessageResponse:
    auth.request_password_reset(data.email)
    return MessageResponse(
        message="Se o e-mail estiver cadastrado, você receberá as instruções para redefinir a senha."
    )


@router.post("/reset-password", response_model=MessageResponse, summary="Redefinir senha com o código recebido")
def reset_password(data: ResetPasswordRequest, auth: Auth) -> MessageResponse:
    auth.reset_password(data.token, data.new_password)
    return MessageResponse(message="Senha redefinida com sucesso.")
