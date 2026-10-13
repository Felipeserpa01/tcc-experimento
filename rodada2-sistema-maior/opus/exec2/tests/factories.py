"""Fábricas de dados para os testes (inserção direta via ORM)."""

import itertools
from datetime import datetime, time, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import security
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, ProfessionalType, Role, Sex
from app.models.patient import HealthInsurance, Patient
from app.models.professional import Availability, Professional
from app.models.user import User

PASSWORD = "Senha@123"
API = "/api/v1"

_sequence = itertools.count(1)


def generate_cpf(base: int) -> str:
    """Gera um CPF válido a partir de um número base (9 primeiros dígitos)."""
    digits = [int(d) for d in f"{base:09d}"[-9:]]
    for position in (9, 10):
        total = sum(d * (position + 1 - i) for i, d in enumerate(digits))
        digits.append((total * 10) % 11 % 10)
    return "".join(map(str, digits))


def make_user(db: Session, role: Role, email: str | None = None, full_name: str = "Usuário Teste") -> User:
    user = User(
        email=email or f"user{next(_sequence)}@clinica.com.br",
        full_name=full_name,
        hashed_password=security.hash_password(PASSWORD),
        role=role,
        is_active=True,
        failed_login_attempts=0,
        token_version=0,
    )
    db.add(user)
    db.commit()
    return user


def make_insurance(
    db: Session, name: str = "Saúde Total", discount: str = "20.00", active: bool = True
) -> HealthInsurance:
    insurance = HealthInsurance(name=name, discount_percent=Decimal(discount), is_active=active)
    db.add(insurance)
    db.commit()
    return insurance


def make_patient(
    db: Session,
    full_name: str = "Maria da Silva",
    insurance: HealthInsurance | None = None,
    with_user: bool = False,
    email: str | None = None,
) -> Patient:
    number = next(_sequence)
    patient = Patient(
        full_name=full_name,
        cpf=generate_cpf(100000000 + number * 7919),
        birth_date=datetime(1990, 5, 20).date(),
        sex=Sex.FEMALE,
        phone="11987654321",
        email=email,
        insurance_id=insurance.id if insurance else None,
        allergies=[],
        is_active=True,
    )
    if with_user:
        patient.user = make_user(
            db, Role.PATIENT, email=email or f"paciente{number}@clinica.com.br", full_name=full_name
        )
    db.add(patient)
    db.commit()
    return patient


def make_doctor(
    db: Session,
    full_name: str = "Carlos Andrade",
    specialty: str = "Cardiologia",
    fee: str | None = "200.00",
    with_user: bool = True,
    weekdays: tuple[int, ...] = (0, 1, 2, 3, 4),
) -> Professional:
    number = next(_sequence)
    doctor = Professional(
        full_name=full_name,
        professional_type=ProfessionalType.DOCTOR,
        crm=f"CRM/SP {100000 + number}",
        specialty=specialty,
        consultation_fee=Decimal(fee) if fee else None,
        is_active=True,
    )
    for weekday in weekdays:
        doctor.availabilities.append(
            Availability(weekday=weekday, start_time=time(8), end_time=time(12), slot_minutes=30)
        )
        doctor.availabilities.append(
            Availability(weekday=weekday, start_time=time(14), end_time=time(18), slot_minutes=30)
        )
    if with_user:
        doctor.user = make_user(db, Role.DOCTOR, email=f"medico{number}@clinica.com.br", full_name=full_name)
    db.add(doctor)
    db.commit()
    return doctor


def make_nurse(db: Session, full_name: str = "Joana Pereira", with_user: bool = True) -> Professional:
    number = next(_sequence)
    nurse = Professional(
        full_name=full_name,
        professional_type=ProfessionalType.NURSE,
        coren=f"COREN/SP {200000 + number}",
        is_active=True,
    )
    if with_user:
        nurse.user = make_user(db, Role.NURSE, email=f"enfermeiro{number}@clinica.com.br", full_name=full_name)
    db.add(nurse)
    db.commit()
    return nurse


def make_appointment(
    db: Session,
    patient: Patient,
    doctor: Professional,
    start: datetime,
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
    minutes: int = 30,
) -> Appointment:
    """Insere uma consulta diretamente (ignora regras de agenda — útil para cenários históricos)."""
    appointment = Appointment(
        patient_id=patient.id,
        professional_id=doctor.id,
        start_at=start,
        end_at=start + timedelta(minutes=minutes),
        status=status,
        reschedule_count=0,
    )
    db.add(appointment)
    db.commit()
    return appointment


def token_for(user: User) -> dict[str, str]:
    token = security.create_access_token(user.id, user.role.value, user.token_version).token
    return {"Authorization": f"Bearer {token}"}
