import enum


class UserRole(str, enum.Enum):
    ADMIN = "administrador"
    DOCTOR = "medico"
    NURSE = "enfermeiro"
    RECEPTIONIST = "recepcionista"
    PATIENT = "paciente"


class ProfessionalType(str, enum.Enum):
    DOCTOR = "medico"
    NURSE = "enfermeiro"


class Sex(str, enum.Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "agendada"
    CONFIRMED = "confirmada"
    IN_PROGRESS = "em_andamento"
    COMPLETED = "realizada"
    CANCELLED = "cancelada"
    NO_SHOW = "faltou"


class BillingStatus(str, enum.Enum):
    PENDING = "pendente"
    PAID = "pago"
    CANCELLED = "cancelado"


class PaymentMethod(str, enum.Enum):
    CASH = "dinheiro"
    CREDIT_CARD = "cartao_credito"
    DEBIT_CARD = "cartao_debito"
    PIX = "pix"
    INSURANCE = "convenio"
