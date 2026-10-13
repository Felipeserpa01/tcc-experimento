from sqlalchemy.orm import Session
from app.models import User
from app.models.user import UserRole
from app.security import hash_password
from app.schemas.user import UserRegister


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user: UserRegister):
    role = UserRole.LIBRARIAN if user.role == "librarian" else UserRole.READER
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hash_password(user.password),
        role=role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
