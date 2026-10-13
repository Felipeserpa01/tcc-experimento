from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.models.enums import AppointmentStatus, ExamStatus
from app.schemas.common import ICD10, InputSchema, NonNull, OutputSchema
from app.schemas.patient import AllergyOut, PatientSummary


class MedicalRecordCreate(InputSchema):
    chief_complaint: str = Field(min_length=3, max_length=2000, description="Queixa principal")
    diagnosis: str = Field(min_length=3, max_length=2000)
    icd10_code: ICD10 | None = Field(default=None, description="Código CID-10 (opcional)")
    notes: str | None = Field(default=None, max_length=5000, description="Observações")


class MedicalRecordUpdate(InputSchema):
    chief_complaint: Annotated[str | None, NonNull, Field(min_length=3, max_length=2000)] = None
    diagnosis: Annotated[str | None, NonNull, Field(min_length=3, max_length=2000)] = None
    icd10_code: ICD10 | None = None
    notes: str | None = Field(default=None, max_length=5000)


class MedicalRecordOut(OutputSchema):
    id: int
    appointment_id: int
    patient_id: int
    professional_id: int
    professional_name: str
    chief_complaint: str
    diagnosis: str
    icd10_code: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PrescriptionItem(InputSchema):
    medication_name: str = Field(min_length=2, max_length=150)
    dosage: str = Field(min_length=1, max_length=100, description="Ex.: 500 mg")
    frequency: str = Field(min_length=1, max_length=100, description="Ex.: a cada 8 horas")
    duration: str = Field(min_length=1, max_length=100, description="Ex.: 7 dias")
    instructions: str | None = Field(default=None, max_length=500)


class PrescriptionCreate(InputSchema):
    items: list[PrescriptionItem] = Field(min_length=1, max_length=20)


class PrescriptionOut(OutputSchema):
    id: int
    appointment_id: int
    patient_id: int
    professional_id: int
    medication_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: str | None
    created_at: datetime


class ExamItem(InputSchema):
    exam_name: str = Field(min_length=2, max_length=150)
    clinical_indication: str | None = Field(default=None, max_length=500)


class ExamRequestCreate(InputSchema):
    exams: list[ExamItem] = Field(min_length=1, max_length=20)


class ExamOut(OutputSchema):
    id: int
    appointment_id: int
    patient_id: int
    professional_id: int
    exam_name: str
    clinical_indication: str | None
    status: ExamStatus
    requested_at: datetime
    result_text: str | None
    has_result_file: bool
    result_file_name: str | None
    result_content_type: str | None
    result_registered_at: datetime | None
    cancelled_at: datetime | None


class ClinicalHistoryEntry(OutputSchema):
    appointment_id: int
    start_at: datetime
    status: AppointmentStatus
    professional_id: int
    professional_name: str
    specialty: str | None
    reason: str | None
    medical_record: MedicalRecordOut | None
    prescriptions: list[PrescriptionOut]
    exams: list[ExamOut]


class ClinicalHistoryOut(OutputSchema):
    patient: PatientSummary
    allergies: list[AllergyOut]
    total_appointments: int
    total_prescriptions: int
    total_exams: int
    entries: list[ClinicalHistoryEntry]
