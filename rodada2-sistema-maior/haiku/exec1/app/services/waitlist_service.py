from datetime import datetime, date, time
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ConflictError
from app.core.enums import WaitlistStatus, AuditAction
from app.models.waitlist import WaitlistEntry
from app.models.user import User
from app.repositories.waitlist_repository import WaitlistRepository
from app.services.audit_service import AuditService


class WaitlistService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = WaitlistRepository(db)
        self.audit_service = AuditService(db)

    def add_to_waitlist(
        self,
        patient_id: int,
        doctor_id: int,
        desired_date: date = None,
        current_user: User = None
    ) -> WaitlistEntry:
        # Check if already on waitlist
        existing = self.db.query(WaitlistEntry).filter(
            WaitlistEntry.patient_id == patient_id,
            WaitlistEntry.doctor_id == doctor_id,
            WaitlistEntry.status == WaitlistStatus.WAITING
        ).first()

        if existing:
            raise ConflictError("Patient is already on waitlist for this doctor")

        entry = self.repository.create({
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "desired_date": desired_date,
            "status": WaitlistStatus.WAITING
        })

        if current_user:
            self.audit_service.log(
                action=AuditAction.APPOINTMENT_CREATED,
                user_id=current_user.id,
                entity_type="WaitlistEntry",
                entity_id=entry.id
            )

        return entry

    def process_freed_slot(self, doctor_id: int, freed_date: date, freed_time: time):
        """Mark waiting patients as notified when a slot opens."""
        waiting = self.repository.get_waiting_for_doctor(doctor_id)

        for entry in waiting:
            if entry.desired_date is None or entry.desired_date == freed_date:
                entry.status = WaitlistStatus.NOTIFIED
                entry.notified_at = datetime.utcnow()
                self.db.add(entry)

        self.db.commit()
