from sqlalchemy.orm import Session
from app.models.refresh_token import RefreshToken
from .base_repository import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, db: Session):
        super().__init__(db, RefreshToken)

    def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        return self.db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    def revoke_user_tokens(self, user_id: int):
        self.db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update(
            {"revoked": True}
        )
        self.db.commit()
