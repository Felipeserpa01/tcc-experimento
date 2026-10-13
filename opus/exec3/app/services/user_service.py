from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserRegister


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Usuário não encontrado.")
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def list_users(db: Session, role: UserRole | None, skip: int, limit: int) -> list[User]:
    stmt = select(User).order_by(User.id).offset(skip).limit(limit)
    if role is not None:
        stmt = stmt.where(User.role == role)
    return list(db.scalars(stmt))


def create_user(db: Session, data: UserRegister, role: UserRole) -> User:
    if get_user_by_email(db, data.email) is not None:
        raise ConflictError("Já existe um usuário cadastrado com este e-mail.")

    user = User(name=data.name, email=data.email, password_hash=hash_password(data.password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if not verify_password(password, user.password_hash if user else None):
        raise AuthenticationError("E-mail ou senha incorretos.")
    return user
