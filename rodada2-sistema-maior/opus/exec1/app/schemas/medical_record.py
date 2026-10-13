"""Schemas de prontuario, prescricoes e exames."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import AppointmentStatus, ExamStatus
from app.schemas.common import ORMModel


class MedicalRecordCreate(BaseModel):
    chief_complaint: str = Field(..., min_length=3, max_length=4000, description="Queixa principal")
    history: str | None = Field(None, max_length=4000)
    physical_exam: str | None = Field(None, max_length=4000)
    diagnosis: str = Field(..., min_length=3, max_length=4000)
    icd10_code: str | None = Field(None, max_length=10)
    treatment_plan: str | None = Field(None, max_length=4000)
    observations: str | None = Field(None, max_length=4000)
    blood_pressure: str | None = Field(None, max_length=15, examples=["120/80"])
    heart_rate: int | None = Field(None, ge=20, le=300)
    temperature_celsius: Decimal | None = Field(None, ge=25, le=45)
    weight_kg: Decimal | None = Field(None, gt=0, le=700)
    height_cm: Decimal | None = Field(None, gt=0, le=300)

    @field_validator("chief_complaint", "diagnosis")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Campo obrigatorio.")
        return value


class MedicalRecordUpdate(BaseModel):
    chief_complaint: str | None = Field(None, min_length=3, max_length=4000)
    history: str | None = Field(None, max_length=4000)
    physical_exam: str | None = Field(None, max_length=4000)
    diagnosis: str | None = Field(None, min_length=3, max_length=4000)
    icd10_code: str | None = Field(None, max_length=10)
    treatment_plan: str | None = Field(None, max_length=4000)
    observations: str | None = Field(None, max_length=4000)
    blood_pressure: str | None = Field(None, max_length=15)
    heart_rate: int | None = Field(None, ge=20, le=300)
    temperature_celsius: Decimal | None = Field(None, ge=25, le=45)
    weight_kg: Decimal | None = Field(None, gt=0, le=700)
    height_cm: Decimal | None = Field(None, gt=0, le=300)


class MedicalRecordRead(ORMModel):
    id: int
    appointment_id: int
    patient_id: int
    professional_id: int
    chief_complaint: str
    history: str | None = None
    physical_exam: str | None = None
    diagnosis: str
    icd10_code: str | None = None
    treatment_plan: str | None = None
    observations: str | None = None
    blood_pressure: str | None = None
    heart_rate: int | None = None
    temperature_celsius: Decimal | None = None
    weight_kg: Decimal | None = None
    height_cm: Decimal | None = None
    recorded_at: datetime
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Prescricoes
# ---------------------------------------------------------------------------
class PrescriptionCreate(BaseModel):
    medication_name: str = Field(..., min_length=2, max_length=150)
    dosage: str = Field(..., min_length=1, max_length=80, examples=["500 mg"])
    frequency: str = Field(..., min_length=1, max_length=80, examples=["8 em 8 horas"])
    duration: str = Field(..., min_length=1, max_length=80, examples=["7 dias"])
    route: str | None = Field(None, max_length=40, examples=["oral"])
    instructions: str | None = Field(None, max_length=2000)

    @field_validator("medication_name", "dosage", "frequency", "duration")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Campo obrigatorio.")
        return value


class PrescriptionUpdate(BaseModel):
    medication_name: str | None = Field(None, min_length=2, max_length=150)
    dosage: str | None = Field(None, min_length=1, max_length=80)
    frequency: str | None = Field(None, min_length=1, max_length=80)
    duration: str | None = Field(None, min_length=1, max_length=80)
    route: str | None = Field(None, max_length=40)
    instructions: str | None = Field(None, max_length=2000)


class PrescriptionRead(ORMModel):
    id: int
    appointment_id: int
    medical_record_id: int | None = None
    patient_id: int
    professional_id: int
    medication_name: str
    dosage: str
    frequency: str
    duration: str
    route: str | None = None
    instructions: str | None = None
    prescribed_at: datetime


# ---------------------------------------------------------------------------
# Exames
# ---------------------------------------------------------------------------
class ExamRequestCreate(BaseModel):
    exam_name: str = Field(..., min_length=2, max_length=150)
    exam_type: str | None = Field(None, max_length=80)
    clinical_indication: str | None = Field(None, max_length=2000)
    price: Decimal = Field(Decimal("0.00"), ge=0, le=Decimal("99999999.99"))

    @field_validator("exam_name")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Nome do exame e obrigatorio.")
        return value


class ExamStatusUpdate(BaseModel):
    status: ExamStatus
    cancellation_reason: str | None = Field(None, max_length=255)


class ExamResultCreate(BaseModel):
    result_summary: str = Field(..., min_length=3, max_length=4000)
    result_notes: str | None = Field(None, max_length=4000)


class ExamAttachmentRead(ORMModel):
    id: int
    exam_id: int
    filename: str
    content_type: str | None = None
    size_bytes: int
    description: str | None = None
    uploaded_by_id: int | None = None
    uploaded_at: datetime


class ExamRequestRead(ORMModel):
    id: int
    appointment_id: int
    medical_record_id: int | None = None
    patient_id: int
    professional_id: int
    exam_name: str
    exam_type: str | None = None
    clinical_indication: str | None = None
    status: ExamStatus
    price: Decimal
    requested_at: datetime
    result_summary: str | None = None
    result_notes: str | None = None
    result_registered_at: datetime | None = None
    cancellation_reason: str | None = None
    attachments: list[ExamAttachmentRead] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Historico clinico
# ---------------------------------------------------------------------------
class ClinicalHistoryEntry(BaseModel):
    appointment_id: int
    scheduled_start: datetime
    status: AppointmentStatus
    professional_id: int
    professional_name: str
    specialty: str | None = None
    medical_record: MedicalRecordRead | None = None
    prescriptions: list[PrescriptionRead] = Field(default_factory=list)
    exams: list[ExamRequestRead] = Field(default_factory=list)


class ClinicalHistoryResponse(BaseModel):
    patient_id: int
    patient_name: str
    total_appointments: int
    entries: list[ClinicalHistoryEntry]
