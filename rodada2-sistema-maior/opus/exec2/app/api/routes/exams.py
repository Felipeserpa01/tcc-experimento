from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import ERROR_RESPONSES, get_clinical_service, require
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.clinical import ExamOut
from app.schemas.common import ErrorResponse
from app.services.clinical_service import ClinicalService

router = APIRouter(prefix="/exams", tags=["Exames"], responses=ERROR_RESPONSES)

Clinical = Annotated[ClinicalService, Depends(get_clinical_service)]
ClinicalReader = Annotated[User, Depends(require(Permission.CLINICAL_READ))]
ClinicalWriter = Annotated[User, Depends(require(Permission.CLINICAL_WRITE))]


@router.get("/{exam_id}", response_model=ExamOut, summary="Detalhar exame")
def get_exam(exam_id: int, actor: ClinicalReader, service: Clinical) -> object:
    return service.get_exam(actor, exam_id)


@router.post(
    "/{exam_id}/result",
    response_model=ExamOut,
    summary="Anexar resultado do exame (médico responsável)",
    responses={
        413: {"model": ErrorResponse, "description": "Arquivo muito grande"},
        415: {"model": ErrorResponse, "description": "Tipo de arquivo não suportado"},
    },
)
def attach_result(
    exam_id: int,
    actor: ClinicalWriter,
    service: Clinical,
    result_text: Annotated[str | None, Form(max_length=10000, description="Laudo/resultado em texto")] = None,
    file: Annotated[UploadFile | None, File(description="PDF, PNG ou JPEG")] = None,
) -> object:
    return service.attach_result(
        actor,
        exam_id,
        result_text=result_text,
        file=file.file if file is not None else None,
        filename=file.filename if file is not None else None,
        content_type=file.content_type if file is not None else None,
    )


@router.get(
    "/{exam_id}/result-file",
    response_class=FileResponse,
    summary="Baixar arquivo de resultado do exame",
)
def download_result(exam_id: int, actor: ClinicalReader, service: Clinical) -> FileResponse:
    path, exam = service.result_file(actor, exam_id)
    return FileResponse(
        path,
        media_type=exam.result_content_type or "application/octet-stream",
        filename=exam.result_file_name or path.name,
    )


@router.post("/{exam_id}/cancel", response_model=ExamOut, summary="Cancelar solicitação de exame")
def cancel_exam(exam_id: int, actor: ClinicalWriter, service: Clinical) -> object:
    return service.cancel_exam(actor, exam_id)
