from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import DbSession, OptionalUser
from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import create_access_token
from app.models.user import UserRole
from app.schemas.auth import Token
from app.schemas.common import ErrorResponse
from app.schemas.user import UserCreate, UserRead
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses={403: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def register(data: UserCreate, db: DbSession, current_user: OptionalUser) -> UserRead:
    """Cadastra um usuário.

    Qualquer pessoa pode se cadastrar como **leitor**. Para cadastrar um **bibliotecário**,
    é necessário estar autenticado como bibliotecário.
    """
    if data.role == UserRole.LIBRARIAN and (current_user is None or not current_user.is_librarian):
        raise ForbiddenError(
            "Apenas bibliotecários autenticados podem cadastrar outros bibliotecários",
            code="librarian_required",
        )
    return user_service.create_user(db, data)


@router.post("/login", response_model=Token, responses={401: {"model": ErrorResponse}})
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> Token:
    """Autentica com e-mail (campo `username`) e senha, retornando um token JWT."""
    user = user_service.authenticate(db, form.username, form.password)
    if user is None:
        raise UnauthorizedError("E-mail ou senha incorretos", code="invalid_credentials")
    return Token(
        access_token=create_access_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )
