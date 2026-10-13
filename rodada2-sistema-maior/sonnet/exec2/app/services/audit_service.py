"""Audit logging service."""
import json
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, db: Session):
        self.repo = AuditRepository(db)

    def log(
        self,
        user_id: int | None,
        action: str,
        entity: str | None = None,
        entity_id: int | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=json.dumps(details, default=str) if details else None,
            ip_address=ip_address,
        )
        return self.repo.create(entry)
