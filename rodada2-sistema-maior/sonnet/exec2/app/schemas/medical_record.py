"""Medical record, prescription and exam schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ExamStatus


class MedicalRecordCreate(BaseModel):
    queixa: str = Field(min_length=3)
    diagnostico: str = Field(min_length=3)
    observacoes: str | None = None


class MedicalRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: int
    queixa: str
    diagnostico: str
    observacoes: str | None
    created_by: int
    created_at: datetime


class PrescriptionCreate(BaseModel):
    medicamento: str = Field(min_length=2, max_length=255)
    dosagem: str = Field(min_length=1, max_length=100)
    frequencia: str = Field(min_length=1, max_length=100)
    duracao: str = Field(min_length=1, max_length=100)


class PrescriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: int
    medicamento: str
    dosagem: str
    frequencia: str
    duracao: str
    created_by: int
    created_at: datetime


class ExamCreate(BaseModel):
    tipo_exame: str = Field(min_length=2, max_length=255)


class ExamResultUpdate(BaseModel):
    resultado: str = Field(min_length=1)


class ExamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: int
    tipo_exame: str
    status: ExamStatus
    resultado: str | None
    solicitado_por: int
    solicitado_em: datetime
    resultado_anexado_em: datetime | None
