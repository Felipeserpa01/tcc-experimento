"""Shared enumerations used across models and schemas."""
import enum


class UserRole(str, enum.Enum):
    ADMIN = "administrador"
    MEDICO = "medico"
    ENFERMEIRO = "enfermeiro"
    RECEPCIONISTA = "recepcionista"
    PACIENTE = "paciente"


STAFF_ROLES = {UserRole.ADMIN, UserRole.MEDICO, UserRole.ENFERMEIRO, UserRole.RECEPCIONISTA}
CLINICAL_ROLES = {UserRole.MEDICO, UserRole.ENFERMEIRO}


class ProfessionalType(str, enum.Enum):
    MEDICO = "medico"
    ENFERMEIRO = "enfermeiro"


class AppointmentStatus(str, enum.Enum):
    AGENDADA = "agendada"
    CONFIRMADA = "confirmada"
    EM_ANDAMENTO = "em_andamento"
    REALIZADA = "realizada"
    CANCELADA = "cancelada"
    FALTOU = "faltou"


TERMINAL_APPOINTMENT_STATUSES = {
    AppointmentStatus.REALIZADA,
    AppointmentStatus.CANCELADA,
    AppointmentStatus.FALTOU,
}


class WaitlistStatus(str, enum.Enum):
    AGUARDANDO = "aguardando"
    NOTIFICADO = "notificado"
    CANCELADO = "cancelado"
    CONVERTIDO = "convertido"


class ExamStatus(str, enum.Enum):
    SOLICITADO = "solicitado"
    RESULTADO_DISPONIVEL = "resultado_disponivel"


class PaymentMethod(str, enum.Enum):
    DINHEIRO = "dinheiro"
    CARTAO_CREDITO = "cartao_credito"
    CARTAO_DEBITO = "cartao_debito"
    PIX = "pix"
    CONVENIO = "convenio"
    BOLETO = "boleto"


class BillingStatus(str, enum.Enum):
    PENDENTE = "pendente"
    PAGO = "pago"
    CANCELADO = "cancelado"


class BillableType(str, enum.Enum):
    CONSULTA = "consulta"
    EXAME = "exame"
