from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, db: Session):
        self.repository = AuditRepository(db)

    def log(
        self,
        user_id: int | None,
        action: str,
        entity: str,
        entity_id: int | str | None = None,
        details: str | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
            ip_address=ip_address,
        )
        return self.repository.create(entry)
