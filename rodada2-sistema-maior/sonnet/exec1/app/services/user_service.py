from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_service import AuditService


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = UserRepository(db)
        self.audit = AuditService(db)

    def create_staff_user(self, payload: UserCreate, acting_user_id: int, ip_address: str | None = None) -> User:
        if self.repository.get_by_email(payload.email):
            raise ConflictError("E-mail já cadastrado.")

        user = User(
            email=payload.email.lower(),
            hashed_password=hash_password(payload.password),
            role=payload.role,
        )
        created = self.repository.create(user)
        self.audit.log(acting_user_id, "CREATE_USER", "User", created.id, ip_address=ip_address)
        return created

    def list_users(self, offset: int, limit: int) -> tuple[list[User], int]:
        return self.repository.list_all(offset, limit)

    def get_user(self, user_id: int) -> User:
        user = self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado.")
        return user

    def update_user(
        self, user_id: int, payload: UserUpdate, acting_user_id: int, ip_address: str | None = None
    ) -> User:
        user = self.get_user(user_id)
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.role is not None:
            user.role = payload.role
        updated = self.repository.update(user)
        self.audit.log(acting_user_id, "UPDATE_USER", "User", user_id, ip_address=ip_address)
        return updated

    def delete_user(self, user_id: int, acting_user_id: int, ip_address: str | None = None) -> None:
        user = self.get_user(user_id)
        self.repository.delete(user)
        self.audit.log(acting_user_id, "DELETE_USER", "User", user_id, ip_address=ip_address)
