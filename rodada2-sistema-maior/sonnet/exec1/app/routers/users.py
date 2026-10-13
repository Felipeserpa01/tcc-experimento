from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, require_roles
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.user_service import UserService
from app.utils.pagination import PageParams

router = APIRouter(prefix="/users", tags=["Usuários"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_staff_user(
    payload: UserCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.create_staff_user(payload, current_user.id, ip_address=get_client_ip(request))


@router.get("", response_model=Page[UserRead])
def list_users(
    params: PageParams = Depends(),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    items, total = service.list_users(params.offset, params.page_size)
    return Page(total=total, page=params.page, page_size=params.page_size, items=items)


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.get_user(user_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.update_user(user_id, payload, current_user.id, ip_address=get_client_ip(request))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    service.delete_user(user_id, current_user.id, ip_address=get_client_ip(request))
