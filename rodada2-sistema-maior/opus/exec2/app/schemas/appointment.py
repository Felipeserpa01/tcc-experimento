from datetime import date, datetime

from pydantic import Field

from app.models.enums import AppointmentStatus, WaitlistStatus
from app.schemas.common import InputSchema, LocalDateTime, OutputSchema
from app.schemas.professional import ProfessionalSummary


class AppointmentCreate(InputSchema):
    patient_id: int | None = Field(
        default=None, gt=0, description="Obrigatório para a equipe; pacientes agendam apenas para si mesmos"
    )
    professional_id: int = Field(gt=0)
    start_at: LocalDateTime = Field(description="Data/hora de início no horário local da clínica")
    reason: str | None = Field(default=None, max_length=500)


class AppointmentReschedule(InputSchema):
    start_at: LocalDateTime


class AppointmentCancel(InputSchema):
    reason: str = Field(min_length=5, max_length=500, description="Motivo do cancelamento")


class AppointmentOut(OutputSchema):
    id: int
    patient_id: int
    patient_name: str
    professional_id: int
    professional_name: str
    specialty: str | None
    start_at: datetime
    end_at: datetime
    status: AppointmentStatus
    reason: str | None
    cancellation_reason: str | None
    cancelled_at: datetime | None
    confirmed_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    no_show_at: datetime | None
    reschedule_count: int
    created_at: datetime
    updated_at: datetime


class DailyAgendaOut(OutputSchema):
    professional: ProfessionalSummary
    date: date
    total: int
    appointments: list[AppointmentOut]


class WaitlistCreate(InputSchema):
    patient_id: int | None = Field(default=None, gt=0)
    professional_id: int = Field(gt=0)
    start_at: LocalDateTime = Field(description="Horário (ocupado) desejado")
    notes: str | None = Field(default=None, max_length=500)


class WaitlistOut(OutputSchema):
    id: int
    patient_id: int
    patient_name: str
    professional_id: int
    professional_name: str
    desired_start_at: datetime
    desired_end_at: datetime
    status: WaitlistStatus
    notes: str | None
    notified_at: datetime | None
    created_at: datetime
