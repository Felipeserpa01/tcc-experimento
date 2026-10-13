from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import func, or_, select, update

from app.core.pagination import PageParams, PageResult, SortParams
from app.models.enums import Role
from app.models.user import PasswordResetToken, RefreshToken, User
from app.repositories.base import BaseRepository, contains_ci


class UserRepository(BaseRepository[User]):
    model = User
    sortable_columns: ClassVar[dict[str, Any]] = {
        "full_name": User.full_name,
        "email": User.email,
        "created_at": User.created_at,
        "last_login_at": User.last_login_at,
    }

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(func.lower(User.email) == email.lower()))

    def email_exists(self, email: str, exclude_id: int | None = None) -> bool:
        stmt = select(User.id).where(func.lower(User.email) == email.lower())
        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)
        return self.db.scalar(stmt) is not None

    def admin_exists(self) -> bool:
        return self.db.scalar(select(User.id).where(User.role == Role.ADMIN).limit(1)) is not None

    def search(
        self,
        page: PageParams,
        sort: SortParams,
        *,
        role: Role | None = None,
        is_active: bool | None = None,
        query: str | None = None,
    ) -> PageResult[User]:
        stmt = select(User)
        if role is not None:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        if query:
            stmt = stmt.where(or_(contains_ci(User.full_name, query), contains_ci(User.email, query)))
        return self.paginate(stmt, page, sort)


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    def get_by_jti(self, jti: str) -> RefreshToken | None:
        return self.db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))

    def revoke_all_for_user(self, user_id: int, when: datetime) -> None:
        self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=when)
        )


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    model = PasswordResetToken

    def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        return self.db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))

    def invalidate_pending_for_user(self, user_id: int, when: datetime) -> None:
        self.db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None))
            .values(used_at=when)
        )
