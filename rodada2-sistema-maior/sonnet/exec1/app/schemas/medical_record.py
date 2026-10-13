from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PrescriptionCreate(BaseModel):
    medication_name: str
    dosage: str
    frequency: str
    duration: str


class PrescriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    medical_record_id: int
    medication_name: str
    dosage: str
    frequency: str
    duration: str
    created_at: datetime


class ExamCreate(BaseModel):
    exam_name: str


class ExamResultUpdate(BaseModel):
    result: str


class ExamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    medical_record_id: int
    exam_name: str
    requested_at: datetime
    result: str | None
    result_attached_at: datetime | None


class MedicalRecordCreate(BaseModel):
    complaint: str
    diagnosis: str
    notes: str | None = None


class MedicalRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: int
    complaint: str
    diagnosis: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    prescriptions: list[PrescriptionRead] = []
    exams: list[ExamRead] = []


class ClinicalHistoryEntry(BaseModel):
    appointment_id: int
    scheduled_at: datetime
    doctor_name: str
    status: str
    medical_record: MedicalRecordRead | None = None
