"""Regras de escopo de acesso (complementam as permissões por perfil)."""

from app.core.exceptions import PermissionDeniedError
from app.models.appointment import Appointment
from app.models.enums import Role
from app.models.professional import Professional
from app.models.user import User

CLINICAL_ROLES = frozenset({Role.DOCTOR, Role.NURSE})
FRONT_DESK_ROLES = frozenset({Role.ADMIN, Role.RECEPTIONIST})


def is_patient(user: User) -> bool:
    return user.role == Role.PATIENT


def own_patient_id(user: User) -> int:
    """ID da ficha do paciente vinculada ao usuário (apenas perfil paciente)."""
    if user.patient is None:
        raise PermissionDeniedError("Usuário paciente sem ficha cadastral vinculada.")
    return user.patient.id


def ensure_patient_scope(user: User, patient_id: int) -> None:
    """Paciente só acessa os próprios dados; a equipe acessa todos."""
    if is_patient(user) and own_patient_id(user) != patient_id:
        raise PermissionDeniedError("Você só pode acessar os seus próprios dados.")


def ensure_own_professional(user: User, professional: Professional) -> None:
    """Médicos/enfermeiros só gerenciam a própria agenda; admin/recepção gerenciam qualquer uma."""
    if user.role in FRONT_DESK_ROLES:
        return
    if user.role in CLINICAL_ROLES and professional.user_id == user.id:
        return
    raise PermissionDeniedError("Você só pode gerenciar a sua própria agenda.")


def is_responsible_doctor(user: User, appointment: Appointment) -> bool:
    return user.role == Role.DOCTOR and appointment.professional.user_id == user.id


def ensure_responsible_doctor(user: User, appointment: Appointment) -> None:
    if not is_responsible_doctor(user, appointment):
        raise PermissionDeniedError("Apenas o médico responsável pela consulta pode realizar esta ação.")


def ensure_appointment_scope(user: User, appointment: Appointment) -> None:
    """Paciente acessa apenas as próprias consultas; a equipe acessa todas."""
    ensure_patient_scope(user, appointment.patient_id)


def ensure_can_manage_appointment(user: User, appointment: Appointment) -> None:
    """Confirmar/cancelar/remarcar: recepção/admin; paciente (própria consulta); médico (própria agenda)."""
    if user.role in FRONT_DESK_ROLES:
        return
    if is_patient(user):
        ensure_patient_scope(user, appointment.patient_id)
        return
    if is_responsible_doctor(user, appointment):
        return
    raise PermissionDeniedError("Você não pode alterar esta consulta.")
