from datetime import datetime
from typing import Annotated

from pydantic import Field, model_validator

from app.models.enums import Role
from app.schemas.common import Email, InputSchema, NonNull, OutputSchema, PersonName, StrongPassword


class UserCreate(InputSchema):
    """Criação de usuário pelo administrador.

    - ``medico``/``enfermeiro`` devem ser vinculados a um profissional (``professional_id``);
    - ``paciente`` deve ser vinculado a uma ficha de paciente (``patient_id``);
    - ``administrador``/``recepcionista`` não possuem vínculo.
    """

    email: Email
    full_name: PersonName
    password: StrongPassword
    role: Role
    patient_id: int | None = Field(default=None, gt=0)
    professional_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _validate_links(self) -> "UserCreate":
        if self.role == Role.PATIENT:
            if self.patient_id is None or self.professional_id is not None:
                raise ValueError("Usuários com perfil paciente exigem apenas 'patient_id'.")
        elif self.role in (Role.DOCTOR, Role.NURSE):
            if self.professional_id is None or self.patient_id is not None:
                raise ValueError("Usuários com perfil médico/enfermeiro exigem apenas 'professional_id'.")
        elif self.patient_id is not None or self.professional_id is not None:
            raise ValueError("Administradores e recepcionistas não podem ser vinculados a pacientes/profissionais.")
        return self


class UserUpdate(InputSchema):
    full_name: Annotated[PersonName | None, NonNull] = None
    email: Annotated[Email | None, NonNull] = None
    is_active: Annotated[bool | None, NonNull] = None


class UserOut(OutputSchema):
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    patient_id: int | None
    professional_id: int | None
    failed_login_attempts: int
    locked_until: datetime | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
