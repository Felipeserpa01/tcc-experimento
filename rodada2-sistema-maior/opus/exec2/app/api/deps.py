"""Dependências FastAPI: sessão, usuário autenticado, permissões, paginação e serviços."""

from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.pagination import PageParams, SortOrder, SortParams
from app.core.permissions import Permission, has_permission
from app.models.user import User
from app.schemas.common import ErrorResponse
from app.services.appointment_service import AppointmentService
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.billing_service import BillingService
from app.services.clinical_service import ClinicalService
from app.services.email import EmailSender, get_email_sender
from app.services.insurance_service import InsuranceService
from app.services.notification_service import NotificationService
from app.services.patient_service import PatientService
from app.services.professional_service import ProfessionalService
from app.services.report_service import ReportService
from app.services.user_service import UserService
from app.services.waitlist_service import WaitlistService

DbSession = Annotated[Session, Depends(get_db)]

bearer_scheme = HTTPBearer(auto_error=False, description="Access token JWT obtido em /auth/login")


# --------------------------------------------------------------------------- serviços
def get_notification_service(
    db: DbSession, sender: Annotated[EmailSender, Depends(get_email_sender)]
) -> NotificationService:
    return NotificationService(db, sender)


Notifications = Annotated[NotificationService, Depends(get_notification_service)]


def get_auth_service(db: DbSession, notifications: Notifications) -> AuthService:
    return AuthService(db, notifications)


def get_appointment_service(db: DbSession, notifications: Notifications) -> AppointmentService:
    return AppointmentService(db, notifications)


def get_waitlist_service(db: DbSession, notifications: Notifications) -> WaitlistService:
    return WaitlistService(db, notifications)


def get_user_service(db: DbSession) -> UserService:
    return UserService(db)


def get_patient_service(db: DbSession) -> PatientService:
    return PatientService(db)


def get_insurance_service(db: DbSession) -> InsuranceService:
    return InsuranceService(db)


def get_professional_service(db: DbSession) -> ProfessionalService:
    return ProfessionalService(db)


def get_clinical_service(db: DbSession) -> ClinicalService:
    return ClinicalService(db)


def get_billing_service(db: DbSession) -> BillingService:
    return BillingService(db)


def get_report_service(db: DbSession) -> ReportService:
    return ReportService(db)


def get_audit_service(db: DbSession) -> AuditService:
    return AuditService(db)


# --------------------------------------------------------------------------- autenticação / autorização
def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    if credentials is None:
        raise AuthenticationError("Token de acesso não informado.", code="token_ausente")
    return auth.authenticate_access_token(credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require(*permissions: Permission) -> Callable[..., User]:
    """Dependência que exige que o perfil do usuário possua todas as permissões informadas."""

    def dependency(user: CurrentUser) -> User:
        missing = [permission.value for permission in permissions if not has_permission(user.role, permission)]
        if missing:
            raise PermissionDeniedError(
                "Seu perfil não possui permissão para esta operação.",
                details={"perfil": user.role.value, "permissoes_necessarias": missing},
            )
        return user

    return dependency


# --------------------------------------------------------------------------- paginação / ordenação
def page_params(
    page: Annotated[int, Query(ge=1, le=100000, description="Página (a partir de 1)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Itens por página (máx. 100)")] = 20,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


Pagination = Annotated[PageParams, Depends(page_params)]


def sorting(*fields: str, default: str, default_order: SortOrder = SortOrder.ASC) -> Callable[..., SortParams]:
    """Cria uma dependência de ordenação aceitando apenas os campos informados (whitelist)."""
    if default not in fields:
        raise ValueError("O campo de ordenação padrão deve estar entre os campos permitidos.")
    sort_field = Literal[fields]  # type: ignore[valid-type]

    def dependency(
        sort_by: Annotated[sort_field, Query(description="Campo de ordenação")] = default,  # type: ignore[valid-type]
        sort_order: Annotated[SortOrder, Query(description="Direção da ordenação")] = default_order,
    ) -> SortParams:
        return SortParams(field=sort_by, order=sort_order)

    return dependency


# --------------------------------------------------------------------------- documentação de erros
ERROR_RESPONSES: dict[int | str, dict] = {
    401: {"model": ErrorResponse, "description": "Não autenticado"},
    403: {"model": ErrorResponse, "description": "Acesso negado"},
    404: {"model": ErrorResponse, "description": "Recurso não encontrado"},
    409: {"model": ErrorResponse, "description": "Conflito com o estado atual"},
    422: {"model": ErrorResponse, "description": "Dados inválidos ou regra de negócio violada"},
}
