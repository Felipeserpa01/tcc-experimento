"""Gestao administrativa de usuarios."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.datetime_utils import now
from app.core.exceptions import (
    BusinessRuleError,
    DuplicateResourceError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.pagination import PaginationParams
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import RefreshTokenRepository, UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_service import AuditAction, AuditService


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------
    def get(self, user_id: int) -> User:
        user = self.repository.get(user_id)
        if user is None:
            raise NotFoundError(f"Usuario {user_id} nao encontrado.")
        return user

    def search(
        self,
        pagination: PaginationParams,
        *,
        query: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]:
        return self.repository.search(
            pagination,
            query=query,
            role=role.value if role else None,
            is_active=is_active,
        )

    # ------------------------------------------------------------------
    def create(self, payload: UserCreate, actor: User) -> User:
        email = payload.email.strip().lower()
        if self.repository.email_taken(email):
            raise DuplicateResourceError("Ja existe um usuario com este email.")

        user = User(
            email=email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role=payload.role,
            is_active=payload.is_active,
        )
        self.db.add(user)
        self.db.flush()

        self.audit.record(
            action=AuditAction.USER_CREATED,
            actor=actor,
            resource_type="user",
            resource_id=user.id,
            description=f"Usuario '{user.email}' criado com perfil '{user.role.value}'.",
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user_id: int, payload: UserUpdate, actor: User) -> User:
        user = self.get(user_id)
        data = payload.model_dump(exclude_unset=True)

        if "email" in data and data["email"]:
            email = data["email"].strip().lower()
            if self.repository.email_taken(email, exclude_user_id=user.id):
                raise DuplicateResourceError("Ja existe um usuario com este email.")
            data["email"] = email

        if "role" in data and data["role"] and data["role"] != user.role:
            self._guard_last_admin(user, new_role=data["role"])

        if "is_active" in data and data["is_active"] is False:
            self._guard_last_admin(user)
            if user.id == actor.id:
                raise BusinessRuleError("Um usuario nao pode desativar a propria conta.")

        for field, value in data.items():
            setattr(user, field, value)
        self.db.flush()

        self.audit.record(
            action=AuditAction.USER_UPDATED,
            actor=actor,
            resource_type="user",
            resource_id=user.id,
            description=f"Usuario '{user.email}' atualizado.",
            extra={"fields": sorted(data.keys())},
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def set_active(self, user_id: int, active: bool, actor: User) -> User:
        user = self.get(user_id)
        if user.id == actor.id and not active:
            raise BusinessRuleError("Um usuario nao pode desativar a propria conta.")
        if not active:
            self._guard_last_admin(user)

        user.is_active = active
        if not active:
            self.refresh_tokens.revoke_all_for_user(user.id)
        self.db.flush()

        self.audit.record(
            action=AuditAction.USER_ACTIVATED if active else AuditAction.USER_DEACTIVATED,
            actor=actor,
            resource_type="user",
            resource_id=user.id,
            description=f"Usuario '{user.email}' {'ativado' if active else 'desativado'}.",
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def unlock(self, user_id: int, actor: User) -> User:
        user = self.get(user_id)
        user.failed_login_attempts = 0
        user.locked_until = None
        self.db.flush()

        self.audit.record(
            action=AuditAction.USER_UNLOCKED,
            actor=actor,
            resource_type="user",
            resource_id=user.id,
            description=f"Bloqueio da conta '{user.email}' removido manualmente.",
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def reset_password_as_admin(self, user_id: int, new_password: str, actor: User) -> User:
        user = self.get(user_id)
        user.hashed_password = hash_password(new_password)
        user.password_changed_at = now()
        user.failed_login_attempts = 0
        user.locked_until = None
        self.refresh_tokens.revoke_all_for_user(user.id)
        self.db.flush()

        self.audit.record(
            action=AuditAction.PASSWORD_CHANGED,
            actor=actor,
            resource_type="user",
            resource_id=user.id,
            description=f"Senha do usuario '{user.email}' redefinida pelo administrador.",
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    # ------------------------------------------------------------------
    def _guard_last_admin(self, user: User, new_role: UserRole | None = None) -> None:
        """Impede que a clinica fique sem nenhum administrador ativo."""
        if user.role != UserRole.ADMIN:
            return
        if new_role == UserRole.ADMIN:
            return
        remaining = (
            self.db.query(User)
            .filter(User.role == UserRole.ADMIN, User.is_active.is_(True), User.id != user.id)
            .count()
        )
        if remaining == 0:
            raise BusinessRuleError(
                "Operacao bloqueada: o sistema ficaria sem nenhum administrador ativo."
            )

    @staticmethod
    def ensure_can_manage(actor: User) -> None:
        if actor.role != UserRole.ADMIN:
            raise PermissionDeniedError("Apenas administradores gerenciam usuarios.")
