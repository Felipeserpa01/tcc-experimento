from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from .base_repository import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, db: Session):
        super().__init__(db, AuditLog)
