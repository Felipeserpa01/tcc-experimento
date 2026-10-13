"""Rotas de prontuario, prescricoes e exames."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.exceptions import PayloadTooLargeError
from app.core.pagination import Page, PaginationParams
from app.db.session import get_db
from app.models.user import User
from app.schemas.medical_record import (
    ExamAttachmentRead,
    ExamRequestCreate,
    ExamRequestRead,
    ExamResultCreate,
    ExamStatusUpdate,
    MedicalRecordCreate,
    MedicalRecordRead,
    MedicalRecordUpdate,
    PrescriptionCreate,
    PrescriptionRead,
    PrescriptionUpdate,
)
from app.services.medical_record_service import MedicalRecordService

settings = get_settings()

appointment_clinical_router = APIRouter(prefix="/appointments", tags=["Prontuario"])
records_router = APIRouter(prefix="/medical-records", tags=["Prontuario"])
prescriptions_router = APIRouter(prefix="/prescriptions", tags=["Prescricoes"])
exams_router = APIRouter(prefix="/exams", tags=["Exames"])


# ---------------------------------------------------------------------------
# Prontuario vinculado a consulta
# ---------------------------------------------------------------------------
@appointment_clinical_router.post(
    "/{appointment_id}/medical-record",
    response_model=MedicalRecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registra o prontuario da consulta (apenas o medico responsavel)",
)
def create_medical_record(
    appointment_id: int,
    payload: MedicalRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MedicalRecordRead:
    return MedicalRecordRead.model_validate(
        MedicalRecordService(db).create_record(appointment_id, payload, current_user)
    )


@appointment_clinical_router.get(
    "/{appointment_id}/medical-record",
    response_model=MedicalRecordRead,
    summary="Prontuario da consulta",
)
def get_medical_record(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MedicalRecordRead:
    return MedicalRecordRead.model_validate(
        MedicalRecordService(db).get_record_by_appointment(appointment_id, current_user)
    )


@records_router.get(
    "", response_model=Page[MedicalRecordRead], summary="Lista prontuarios com filtros"
)
def list_medical_records(
    pagination: PaginationParams = Depends(),
    patient_id: int | None = Query(None),
    professional_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[MedicalRecordRead]:
    items, total = MedicalRecordService(db).search_records(
        pagination, current_user, patient_id=patient_id, professional_id=professional_id
    )
    return Page.create(
        [MedicalRecordRead.model_validate(item) for item in items],
        total,
        pagination.page,
        pagination.size,
    )


@records_router.get("/{record_id}", response_model=MedicalRecordRead, summary="Detalha prontuario")
def get_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MedicalRecordRead:
    return MedicalRecordRead.model_validate(
        MedicalRecordService(db).get_record(record_id, current_user)
    )


@records_router.patch(
    "/{record_id}",
    response_model=MedicalRecordRead,
    summary="Atualiza o prontuario (apenas o medico responsavel)",
)
def update_record(
    record_id: int,
    payload: MedicalRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MedicalRecordRead:
    return MedicalRecordRead.model_validate(
        MedicalRecordService(db).update_record(record_id, payload, current_user)
    )


# ---------------------------------------------------------------------------
# Prescricoes
# ---------------------------------------------------------------------------
@appointment_clinical_router.post(
    "/{appointment_id}/prescriptions",
    response_model=PrescriptionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registra prescricao na consulta (apenas o medico responsavel)",
)
def create_prescription(
    appointment_id: int,
    payload: PrescriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PrescriptionRead:
    return PrescriptionRead.model_validate(
        MedicalRecordService(db).create_prescription(appointment_id, payload, current_user)
    )


@appointment_clinical_router.get(
    "/{appointment_id}/prescriptions",
    response_model=list[PrescriptionRead],
    summary="Prescricoes da consulta",
)
def list_prescriptions(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PrescriptionRead]:
    items = MedicalRecordService(db).list_prescriptions(appointment_id, current_user)
    return [PrescriptionRead.model_validate(item) for item in items]


@prescriptions_router.patch(
    "/{prescription_id}", response_model=PrescriptionRead, summary="Atualiza uma prescricao"
)
def update_prescription(
    prescription_id: int,
    payload: PrescriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PrescriptionRead:
    return PrescriptionRead.model_validate(
        MedicalRecordService(db).update_prescription(prescription_id, payload, current_user)
    )


@prescriptions_router.delete(
    "/{prescription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Remove uma prescricao",
)
def delete_prescription(
    prescription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    MedicalRecordService(db).delete_prescription(prescription_id, current_user)


# ---------------------------------------------------------------------------
# Exames
# ---------------------------------------------------------------------------
@appointment_clinical_router.post(
    "/{appointment_id}/exams",
    response_model=ExamRequestRead,
    status_code=status.HTTP_201_CREATED,
    summary="Solicita exame na consulta (apenas o medico responsavel)",
)
def create_exam(
    appointment_id: int,
    payload: ExamRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExamRequestRead:
    return ExamRequestRead.model_validate(
        MedicalRecordService(db).create_exam(appointment_id, payload, current_user)
    )


@appointment_clinical_router.get(
    "/{appointment_id}/exams",
    response_model=list[ExamRequestRead],
    summary="Exames solicitados na consulta",
)
def list_exams(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ExamRequestRead]:
    items = MedicalRecordService(db).list_exams(appointment_id, current_user)
    return [ExamRequestRead.model_validate(item) for item in items]


@exams_router.get("/{exam_id}", response_model=ExamRequestRead, summary="Detalha um exame")
def get_exam(
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExamRequestRead:
    return ExamRequestRead.model_validate(MedicalRecordService(db).get_exam(exam_id, current_user))


@exams_router.patch(
    "/{exam_id}/status", response_model=ExamRequestRead, summary="Atualiza o status do exame"
)
def update_exam_status(
    exam_id: int,
    payload: ExamStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExamRequestRead:
    return ExamRequestRead.model_validate(
        MedicalRecordService(db).update_exam_status(exam_id, payload, current_user)
    )


@exams_router.post(
    "/{exam_id}/result", response_model=ExamRequestRead, summary="Registra o resultado do exame"
)
def register_exam_result(
    exam_id: int,
    payload: ExamResultCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExamRequestRead:
    return ExamRequestRead.model_validate(
        MedicalRecordService(db).register_exam_result(exam_id, payload, current_user)
    )


@exams_router.post(
    "/{exam_id}/attachments",
    response_model=ExamAttachmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Anexa o arquivo de resultado do exame",
)
async def upload_exam_attachment(
    exam_id: int,
    file: UploadFile = File(..., description="Arquivo com o resultado do exame"),
    description: str | None = Form(None, max_length=255),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExamAttachmentRead:
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise PayloadTooLargeError(
            f"Arquivo acima do limite de {settings.max_upload_size_mb} MB."
        )
    attachment = MedicalRecordService(db).attach_exam_result(
        exam_id,
        filename=file.filename or "resultado",
        content=content,
        content_type=file.content_type,
        description=description,
        actor=current_user,
    )
    return ExamAttachmentRead.model_validate(attachment)


@exams_router.get(
    "/{exam_id}/attachments",
    response_model=list[ExamAttachmentRead],
    summary="Lista os anexos do exame",
)
def list_attachments(
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ExamAttachmentRead]:
    items = MedicalRecordService(db).list_attachments(exam_id, current_user)
    return [ExamAttachmentRead.model_validate(item) for item in items]


@exams_router.get(
    "/attachments/{attachment_id}/download",
    response_class=FileResponse,
    summary="Baixa o arquivo de resultado",
)
def download_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    attachment = MedicalRecordService(db).get_attachment_for_download(attachment_id, current_user)
    return FileResponse(
        path=attachment.stored_path,
        filename=attachment.filename,
        media_type=attachment.content_type or "application/octet-stream",
    )
