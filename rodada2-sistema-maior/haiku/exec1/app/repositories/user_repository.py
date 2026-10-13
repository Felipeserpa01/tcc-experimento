from sqlalchemy.orm import Session
from app.models.user import User
from .base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(db, User)

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_role(self, role: str):
        return self.db.query(User).filter(User.role == role).all()
