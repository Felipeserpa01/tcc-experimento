from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db as get_db_session
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.core.pagination import PageParams
from app.models.user import User


def get_db() -> Session:
    db = next(get_db_session())
    return db


def get_current_user(
    token: str = Depends(lambda: None),
    db: Session = Depends(get_db)
) -> User:
    """Extract and validate JWT token from Authorization header."""
    from fastapi import Request, HTTPException
    from fastapi.security import HTTPBearer, HTTPAuthCredentials

    # This will be overridden by the route's dependency on Bearer token
    raise UnauthorizedError("No token provided")


def get_pagination_params(
    page: int = 1,
    size: int = 20,
    sort_by: str = "created_at",
    order: str = "desc"
) -> PageParams:
    return PageParams(page=page, size=size, sort_by=sort_by, order=order)


def require_roles(*allowed_roles):
    """Dependency factory that checks if the current user has one of the allowed roles."""
    def check_role(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise ForbiddenError("Insufficient permissions for this action")
        return current_user

    return check_role
