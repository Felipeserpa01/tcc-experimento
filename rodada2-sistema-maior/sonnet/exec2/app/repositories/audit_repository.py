"""Data access for AuditLog."""
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, log: AuditLog) -> AuditLog:
        self.db.add(log)
        self.db.flush()
        return log
