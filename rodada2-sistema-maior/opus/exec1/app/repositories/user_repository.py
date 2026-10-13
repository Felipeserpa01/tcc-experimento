"""Repositorios de usuario, tokens e notificacoes."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select, update

from app.core.datetime_utils import now
from app.core.pagination import PaginationParams
from app.models.notification import Notification
from app.models.user import PasswordResetToken, RefreshToken, User
from app.repositories.base import BaseRepository

USER_SORT_FIELDS = {
    "id": User.id,
    "email": User.email,
    "full_name": User.full_name,
    "role": User.role,
    "created_at": User.created_at,
    "last_login_at": User.last_login_at,
}


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        normalized = (email or "").strip().lower()
        stmt = select(User).where(func.lower(User.email) == normalized).limit(1)
        return self.db.execute(stmt).scalars().first()

    def email_taken(self, email: str, *, exclude_user_id: int | None = None) -> bool:
        normalized = (email or "").strip().lower()
        stmt = select(func.count()).select_from(User).where(func.lower(User.email) == normalized)
        if exclude_user_id:
            stmt = stmt.where(User.id != exclude_user_id)
        return (self.db.execute(stmt).scalar_one() or 0) > 0

    def search(
        self,
        pagination: PaginationParams,
        *,
        query: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]:
        stmt = select(User)
        if query:
            like = f"%{query.strip()}%"
            stmt = stmt.where(or_(User.full_name.ilike(like), User.email.ilike(like)))
        if role:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active.is_(is_active))

        column, descending = pagination.resolve_sort(USER_SORT_FIELDS, "created_at")
        stmt = self.apply_order(stmt, column, descending)
        return self.paginate(stmt, pagination.page, pagination.size)


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    def get_by_jti(self, jti: str) -> RefreshToken | None:
        return self.get_by(jti=jti)

    def get_active_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now(),
            )
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def revoke_all_for_user(self, user_id: int) -> int:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now())
        )
        result = self.db.execute(stmt)
        self.db.flush()
        return result.rowcount or 0

    def purge_expired(self, reference: datetime | None = None) -> int:
        reference = reference or now()
        stmt = select(RefreshToken).where(RefreshToken.expires_at < reference)
        tokens = self.db.execute(stmt).scalars().all()
        for token in tokens:
            self.db.delete(token)
        self.db.flush()
        return len(tokens)


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    model = PasswordResetToken

    def get_usable(self, token_hash: str) -> PasswordResetToken | None:
        stmt = (
            select(PasswordResetToken)
            .where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now(),
            )
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def invalidate_for_user(self, user_id: int) -> int:
        stmt = (
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=now())
        )
        result = self.db.execute(stmt)
        self.db.flush()
        return result.rowcount or 0


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    def list_for_user(
        self, user_id: int, pagination: PaginationParams, *, only_unread: bool = False
    ) -> tuple[list[Notification], int]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if only_unread:
            stmt = stmt.where(Notification.read_at.is_(None))
        stmt = stmt.order_by(Notification.created_at.desc(), Notification.id.desc())
        return self.paginate(stmt, pagination.page, pagination.size)

    def mark_all_read(self, user_id: int) -> int:
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=now())
        )
        result = self.db.execute(stmt)
        self.db.flush()
        return result.rowcount or 0
