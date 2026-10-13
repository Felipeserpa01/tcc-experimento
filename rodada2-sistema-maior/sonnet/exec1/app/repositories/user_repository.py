from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.token import PasswordResetToken, RefreshToken
from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self, offset: int, limit: int) -> tuple[list[User], int]:
        total = self.db.execute(select(User)).scalars().all()
        stmt = select(User).order_by(User.id).offset(offset).limit(limit)
        items = self.db.execute(stmt).scalars().all()
        return items, len(total)

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User) -> User:
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()

    def save_refresh_token(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_refresh_token(self, jti: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.jti == jti)
        return self.db.execute(stmt).scalar_one_or_none()

    def revoke_refresh_token(self, token: RefreshToken) -> None:
        token.revoked = True
        self.db.commit()

    def save_password_reset_token(self, token: PasswordResetToken) -> PasswordResetToken:
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_password_reset_token(self, token: str) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(PasswordResetToken.token == token)
        return self.db.execute(stmt).scalar_one_or_none()
