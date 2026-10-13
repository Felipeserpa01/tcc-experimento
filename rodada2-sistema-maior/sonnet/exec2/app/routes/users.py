"""Admin user-management endpoints (staff accounts)."""
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.database import get_db
from app.dependencies import get_client_ip, require_roles
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import StaffUserCreate, UserOut
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Usuários (Admin)"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_staff_user(
    payload: StaffUserCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.create_staff_user(payload, current_user, ip_address=get_client_ip(request))


@router.get("", response_model=PaginatedResponse[UserOut])
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    items, total = service.list_users(page, page_size)
    return PaginatedResponse.build(items, total, page, page_size)


@router.patch("/{user_id}/activate", response_model=UserOut)
def activate_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.set_active_status(user_id, True, current_user, ip_address=get_client_ip(request))


@router.patch("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.set_active_status(user_id, False, current_user, ip_address=get_client_ip(request))
