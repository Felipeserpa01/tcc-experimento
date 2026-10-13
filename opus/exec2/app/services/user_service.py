from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ConflictError, InvalidOperationError, NotFoundError
from app.core.security import hash_password, simulate_password_check, verify_password
from app.models import User, UserRole
from app.schemas.user import UserCreate

EMAIL_TAKEN_MESSAGE = "Já existe um usuário cadastrado com este e-mail"
INVALID_CREDENTIALS_MESSAGE = "E-mail ou senha inválidos"


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Usuário não encontrado", code="user_not_found")
    return user


def get_reader(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Leitor não encontrado", code="reader_not_found")
    if user.role != UserRole.READER:
        raise InvalidOperationError("O usuário informado não é um leitor", code="user_not_reader")
    return user


def create_user(db: Session, data: UserCreate) -> User:
    if get_user_by_email(db, data.email) is not None:
        raise ConflictError(EMAIL_TAKEN_MESSAGE, code="email_already_registered")

    user = User(
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:  # cadastro simultâneo com o mesmo e-mail
        db.rollback()
        raise ConflictError(EMAIL_TAKEN_MESSAGE, code="email_already_registered") from exc
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None:
        simulate_password_check()
        raise AuthenticationError(INVALID_CREDENTIALS_MESSAGE, code="invalid_credentials")
    if not verify_password(password, user.hashed_password):
        raise AuthenticationError(INVALID_CREDENTIALS_MESSAGE, code="invalid_credentials")
    return user


def list_users(db: Session, *, role: UserRole | None, skip: int, limit: int) -> tuple[list[User], int]:
    filters = [User.role == role] if role is not None else []
    total = db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
    users = db.scalars(select(User).where(*filters).order_by(User.name, User.id).offset(skip).limit(limit)).all()
    return list(users), total
