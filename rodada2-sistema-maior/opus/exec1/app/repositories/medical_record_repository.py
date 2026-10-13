"""Repositorios de prontuario, prescricoes e exames."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.core.datetime_utils import range_bounds
from app.core.pagination import PaginationParams
from app.models.enums import ExamStatus
from app.models.medical_record import ExamAttachment, ExamRequest, MedicalRecord, Prescription
from app.repositories.base import BaseRepository

MEDICAL_RECORD_SORT_FIELDS = {
    "id": MedicalRecord.id,
    "recorded_at": MedicalRecord.recorded_at,
    "created_at": MedicalRecord.created_at,
}


class MedicalRecordRepository(BaseRepository[MedicalRecord]):
    model = MedicalRecord

    def get_by_appointment(self, appointment_id: int) -> MedicalRecord | None:
        return self.get_by(appointment_id=appointment_id)

    def list_for_patient(self, patient_id: int) -> list[MedicalRecord]:
        stmt = (
            select(MedicalRecord)
            .where(MedicalRecord.patient_id == patient_id)
            .order_by(MedicalRecord.recorded_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def search(
        self,
        pagination: PaginationParams,
        *,
        patient_id: int | None = None,
        professional_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[MedicalRecord], int]:
        stmt = select(MedicalRecord)
        if patient_id is not None:
            stmt = stmt.where(MedicalRecord.patient_id == patient_id)
        if professional_id is not None:
            stmt = stmt.where(MedicalRecord.professional_id == professional_id)
        start, end = range_bounds(start_date, end_date)
        if start is not None:
            stmt = stmt.where(MedicalRecord.recorded_at >= start)
        if end is not None:
            stmt = stmt.where(MedicalRecord.recorded_at < end)

        column, descending = pagination.resolve_sort(MEDICAL_RECORD_SORT_FIELDS, "recorded_at")
        stmt = self.apply_order(stmt, column, descending)
        return self.paginate(stmt, pagination.page, pagination.size)


class PrescriptionRepository(BaseRepository[Prescription]):
    model = Prescription

    def list_for_appointment(self, appointment_id: int) -> list[Prescription]:
        stmt = (
            select(Prescription)
            .where(Prescription.appointment_id == appointment_id)
            .order_by(Prescription.id.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_for_patient(self, patient_id: int) -> list[Prescription]:
        stmt = (
            select(Prescription)
            .where(Prescription.patient_id == patient_id)
            .order_by(Prescription.prescribed_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def search(
        self,
        pagination: PaginationParams,
        *,
        patient_id: int | None = None,
        appointment_id: int | None = None,
        medication: str | None = None,
    ) -> tuple[list[Prescription], int]:
        stmt = select(Prescription)
        if patient_id is not None:
            stmt = stmt.where(Prescription.patient_id == patient_id)
        if appointment_id is not None:
            stmt = stmt.where(Prescription.appointment_id == appointment_id)
        if medication:
            stmt = stmt.where(Prescription.medication_name.ilike(f"%{medication.strip()}%"))
        stmt = stmt.order_by(Prescription.prescribed_at.desc())
        return self.paginate(stmt, pagination.page, pagination.size)


class ExamRepository(BaseRepository[ExamRequest]):
    model = ExamRequest

    def list_for_appointment(self, appointment_id: int) -> list[ExamRequest]:
        stmt = (
            select(ExamRequest)
            .where(ExamRequest.appointment_id == appointment_id)
            .order_by(ExamRequest.id.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_for_patient(self, patient_id: int) -> list[ExamRequest]:
        stmt = (
            select(ExamRequest)
            .where(ExamRequest.patient_id == patient_id)
            .order_by(ExamRequest.requested_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def search(
        self,
        pagination: PaginationParams,
        *,
        patient_id: int | None = None,
        appointment_id: int | None = None,
        status: ExamStatus | None = None,
    ) -> tuple[list[ExamRequest], int]:
        stmt = select(ExamRequest)
        if patient_id is not None:
            stmt = stmt.where(ExamRequest.patient_id == patient_id)
        if appointment_id is not None:
            stmt = stmt.where(ExamRequest.appointment_id == appointment_id)
        if status is not None:
            stmt = stmt.where(ExamRequest.status == status)
        stmt = stmt.order_by(ExamRequest.requested_at.desc())
        return self.paginate(stmt, pagination.page, pagination.size)


class ExamAttachmentRepository(BaseRepository[ExamAttachment]):
    model = ExamAttachment

    def list_for_exam(self, exam_id: int) -> list[ExamAttachment]:
        stmt = (
            select(ExamAttachment)
            .where(ExamAttachment.exam_id == exam_id)
            .order_by(ExamAttachment.uploaded_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())
