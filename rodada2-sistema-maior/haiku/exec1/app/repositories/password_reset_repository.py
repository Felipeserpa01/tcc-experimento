from sqlalchemy.orm import Session
from app.models.password_reset import PasswordResetToken
from .base_repository import BaseRepository


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    def __init__(self, db: Session):
        super().__init__(db, PasswordResetToken)

    def get_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        return self.db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == token_hash
        ).first()
