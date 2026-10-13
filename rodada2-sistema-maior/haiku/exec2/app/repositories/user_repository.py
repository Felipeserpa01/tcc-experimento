from sqlalchemy.orm import Session
from app.models import User, UserRole

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int):
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()

    def get_by_username(self, username: str):
        return self.db.query(User).filter(User.username == username).first()

    def get_by_role(self, role: UserRole, skip: int = 0, limit: int = 100):
        return self.db.query(User).filter(User.role == role).offset(skip).limit(limit).all()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(User).offset(skip).limit(limit).all()

    def create(self, user: User):
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User):
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user_id: int):
        user = self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False
