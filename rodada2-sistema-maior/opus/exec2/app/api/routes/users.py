from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ERROR_RESPONSES, Pagination, get_user_service, require, sorting
from app.core.pagination import SortParams
from app.core.permissions import Permission
from app.models.enums import Role
from app.models.user import User
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Usuários"], responses=ERROR_RESPONSES)

Admin = Annotated[User, Depends(require(Permission.USERS_MANAGE))]
Users = Annotated[UserService, Depends(get_user_service)]
UserSort = Annotated[
    SortParams, Depends(sorting("full_name", "email", "created_at", "last_login_at", default="full_name"))
]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Criar usuário")
def create_user(data: UserCreate, actor: Admin, service: Users) -> object:
    return service.create(actor, data)


@router.get("", response_model=Page[UserOut], summary="Listar usuários")
def list_users(
    _: Admin,
    service: Users,
    page: Pagination,
    sort: UserSort,
    role: Role | None = None,
    is_active: bool | None = None,
    q: Annotated[str | None, Query(min_length=2, max_length=100, description="Busca por nome ou e-mail")] = None,
) -> object:
    return service.search(page, sort, role=role, is_active=is_active, query=q)


@router.get("/{user_id}", response_model=UserOut, summary="Detalhar usuário")
def get_user(user_id: int, _: Admin, service: Users) -> object:
    return service.get(user_id)


@router.patch("/{user_id}", response_model=UserOut, summary="Atualizar usuário (nome, e-mail, ativo)")
def update_user(user_id: int, data: UserUpdate, actor: Admin, service: Users) -> object:
    return service.update(actor, user_id, data)


@router.post("/{user_id}/unlock", response_model=UserOut, summary="Desbloquear conta bloqueada por tentativas")
def unlock_user(user_id: int, actor: Admin, service: Users) -> object:
    return service.unlock(actor, user_id)
