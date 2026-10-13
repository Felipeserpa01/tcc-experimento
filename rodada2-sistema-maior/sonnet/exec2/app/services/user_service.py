"""Admin user-management service: staff account creation and activation control."""
from sqlalchemy import asc, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import StaffUserCreate
from app.services.audit_service import AuditService


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)
        self.audit = AuditService(db)

    def create_staff_user(self, data: StaffUserCreate, actor: User, ip_address: str | None = None) -> User:
        if self.repo.get_by_email(data.email):
            raise ConflictError("Já existe um usuário cadastrado com este e-mail.")

        user = User(email=data.email.lower(), hashed_password=hash_password(data.password), role=data.role)
        self.repo.create(user)
        self.db.commit()
        self.audit.log(actor.id, "STAFF_USER_CREATE", "User", user.id, ip_address=ip_address)
        self.db.commit()
        return user

    def list_users(self, page: int, page_size: int) -> tuple[list[User], int]:
        stmt = select(User).order_by(asc(User.created_at)).offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.execute(stmt).scalars().all())
        total = self.db.execute(select(func.count()).select_from(User)).scalar_one()
        return items, total

    def set_active_status(
        self, user_id: int, is_active: bool, actor: User, ip_address: str | None = None
    ) -> User:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("Usuário não encontrado.")
        user.is_active = is_active
        self.repo.update(user)
        self.db.commit()
        action = "USER_ACTIVATE" if is_active else "USER_DEACTIVATE"
        self.audit.log(actor.id, action, "User", user.id, ip_address=ip_address)
        self.db.commit()
        return user
