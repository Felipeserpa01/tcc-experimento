"""Rotas administrativas de usuarios."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.core.pagination import Page, PaginationParams
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cria usuario interno (apenas administrador)",
)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserRead:
    return UserRead.model_validate(UserService(db).create(payload, current_user))


@router.get("", response_model=Page[UserRead], summary="Lista usuarios com filtros e paginacao")
def list_users(
    pagination: PaginationParams = Depends(),
    query: str | None = Query(None, description="Busca por nome ou email"),
    role: UserRole | None = Query(None),
    is_active: bool | None = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Page[UserRead]:
    items, total = UserService(db).search(
        pagination, query=query, role=role, is_active=is_active
    )
    return Page.create(
        [UserRead.model_validate(item) for item in items], total, pagination.page, pagination.size
    )


@router.get("/{user_id}", response_model=UserRead, summary="Detalha um usuario")
def get_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserRead:
    return UserRead.model_validate(UserService(db).get(user_id))


@router.patch("/{user_id}", response_model=UserRead, summary="Atualiza um usuario")
def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserRead:
    return UserRead.model_validate(UserService(db).update(user_id, payload, current_user))


@router.post("/{user_id}/activate", response_model=UserRead, summary="Ativa um usuario")
def activate_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserRead:
    return UserRead.model_validate(UserService(db).set_active(user_id, True, current_user))


@router.post("/{user_id}/deactivate", response_model=UserRead, summary="Desativa um usuario")
def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserRead:
    return UserRead.model_validate(UserService(db).set_active(user_id, False, current_user))


@router.post(
    "/{user_id}/unlock",
    response_model=UserRead,
    summary="Remove o bloqueio por tentativas de login",
)
def unlock_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserRead:
    return UserRead.model_validate(UserService(db).unlock(user_id, current_user))


@router.post(
    "/{user_id}/reset-password",
    response_model=MessageResponse,
    summary="Redefine a senha de um usuario (administrador)",
)
def reset_user_password(
    user_id: int,
    new_password: str = Body(..., embed=True, min_length=8, max_length=72),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MessageResponse:
    UserService(db).reset_password_as_admin(user_id, new_password, current_user)
    return MessageResponse(message="Senha redefinida. As sessoes do usuario foram encerradas.")
