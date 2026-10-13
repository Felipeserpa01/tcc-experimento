"""Controle de acesso granular.

Cada endpoint exige uma ou mais *permissões*; cada perfil (papel) recebe um conjunto
de permissões. Regras de escopo (ex.: paciente só acessa os próprios dados, apenas o
médico responsável registra o prontuário) são aplicadas na camada de serviços.
"""

from enum import StrEnum

from app.models.enums import Role


class Permission(StrEnum):
    USERS_MANAGE = "users:manage"
    AUDIT_READ = "audit:read"

    INSURANCES_READ = "insurances:read"
    INSURANCES_MANAGE = "insurances:manage"

    PATIENTS_CREATE = "patients:create"
    PATIENTS_READ = "patients:read"
    PATIENTS_UPDATE = "patients:update"
    PATIENTS_DELETE = "patients:delete"

    PROFESSIONALS_READ = "professionals:read"
    PROFESSIONALS_MANAGE = "professionals:manage"
    AVAILABILITY_MANAGE = "availability:manage"

    APPOINTMENTS_READ = "appointments:read"
    APPOINTMENTS_CREATE = "appointments:create"
    APPOINTMENTS_MANAGE = "appointments:manage"
    APPOINTMENTS_ATTEND = "appointments:attend"
    APPOINTMENTS_NO_SHOW = "appointments:no_show"
    AGENDA_READ = "agenda:read"

    WAITLIST_READ = "waitlist:read"
    WAITLIST_MANAGE = "waitlist:manage"

    CLINICAL_READ = "clinical:read"
    CLINICAL_WRITE = "clinical:write"

    BILLING_READ = "billing:read"
    BILLING_MANAGE = "billing:manage"

    REPORTS_READ = "reports:read"


_P = Permission

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(
        {
            _P.USERS_MANAGE,
            _P.AUDIT_READ,
            _P.INSURANCES_READ,
            _P.INSURANCES_MANAGE,
            _P.PATIENTS_CREATE,
            _P.PATIENTS_READ,
            _P.PATIENTS_UPDATE,
            _P.PATIENTS_DELETE,
            _P.PROFESSIONALS_READ,
            _P.PROFESSIONALS_MANAGE,
            _P.AVAILABILITY_MANAGE,
            _P.APPOINTMENTS_READ,
            _P.APPOINTMENTS_CREATE,
            _P.APPOINTMENTS_MANAGE,
            _P.APPOINTMENTS_NO_SHOW,
            _P.AGENDA_READ,
            _P.WAITLIST_READ,
            _P.WAITLIST_MANAGE,
            _P.BILLING_READ,
            _P.BILLING_MANAGE,
            _P.REPORTS_READ,
        }
    ),
    Role.RECEPTIONIST: frozenset(
        {
            _P.INSURANCES_READ,
            _P.PATIENTS_CREATE,
            _P.PATIENTS_READ,
            _P.PATIENTS_UPDATE,
            _P.PROFESSIONALS_READ,
            _P.AVAILABILITY_MANAGE,
            _P.APPOINTMENTS_READ,
            _P.APPOINTMENTS_CREATE,
            _P.APPOINTMENTS_MANAGE,
            _P.APPOINTMENTS_NO_SHOW,
            _P.AGENDA_READ,
            _P.WAITLIST_READ,
            _P.WAITLIST_MANAGE,
            _P.BILLING_READ,
            _P.BILLING_MANAGE,
        }
    ),
    Role.DOCTOR: frozenset(
        {
            _P.INSURANCES_READ,
            _P.PATIENTS_READ,
            _P.PATIENTS_UPDATE,
            _P.PROFESSIONALS_READ,
            _P.AVAILABILITY_MANAGE,
            _P.APPOINTMENTS_READ,
            _P.APPOINTMENTS_MANAGE,
            _P.APPOINTMENTS_ATTEND,
            _P.APPOINTMENTS_NO_SHOW,
            _P.AGENDA_READ,
            _P.WAITLIST_READ,
            _P.CLINICAL_READ,
            _P.CLINICAL_WRITE,
        }
    ),
    Role.NURSE: frozenset(
        {
            _P.INSURANCES_READ,
            _P.PATIENTS_READ,
            _P.PATIENTS_UPDATE,
            _P.PROFESSIONALS_READ,
            _P.AVAILABILITY_MANAGE,
            _P.APPOINTMENTS_READ,
            _P.AGENDA_READ,
            _P.WAITLIST_READ,
            _P.CLINICAL_READ,
        }
    ),
    Role.PATIENT: frozenset(
        {
            _P.INSURANCES_READ,
            _P.PATIENTS_READ,
            _P.PATIENTS_UPDATE,
            _P.PROFESSIONALS_READ,
            _P.APPOINTMENTS_READ,
            _P.APPOINTMENTS_CREATE,
            _P.APPOINTMENTS_MANAGE,
            _P.WAITLIST_READ,
            _P.WAITLIST_MANAGE,
            _P.CLINICAL_READ,
            _P.BILLING_READ,
        }
    ),
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
