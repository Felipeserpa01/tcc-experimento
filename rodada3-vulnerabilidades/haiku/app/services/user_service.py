from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import PASSWORD_MAX_LENGTH, UserCreate

# Usado quando o e-mail não existe, para que o tempo de resposta do login não revele
# quais e-mails estão cadastrados.
_DUMMY_HASH = hash_password("senha-ficticia-para-equalizar-tempo")


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Usuário não encontrado", code="user_not_found")
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def create_user(db: Session, data: UserCreate) -> User:
    if get_user_by_email(db, data.email) is not None:
        raise ConflictError("Já existe um usuário com este e-mail", code="email_already_registered")

    user = User(
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    # Senhas acima do limite do cadastro nunca são válidas; recusá-las antes do Argon2
    # evita gastar CPU com entradas enormes. Não depende do e-mail, então não vaza informação.
    if len(password) > PASSWORD_MAX_LENGTH:
        return None
    user = get_user_by_email(db, email.strip())
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    return user if verify_password(password, user.hashed_password) else None


def list_users(db: Session, role: UserRole | None, skip: int, limit: int) -> tuple[list[User], int]:
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    users = db.scalars(stmt.order_by(User.name, User.id).offset(skip).limit(limit)).all()
    return list(users), total


def ensure_first_librarian(db: Session) -> None:
    """Cria o bibliotecário inicial definido nas configurações, caso ainda não exista."""
    if not (settings.first_librarian_email and settings.first_librarian_password):
        return
    if get_user_by_email(db, settings.first_librarian_email) is not None:
        return

    create_user(
        db,
        UserCreate(
            name=settings.first_librarian_name,
            email=settings.first_librarian_email,
            password=settings.first_librarian_password,
            role=UserRole.LIBRARIAN,
        ),
    )
