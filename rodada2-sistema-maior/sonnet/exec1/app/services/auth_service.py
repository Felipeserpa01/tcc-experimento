from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import (
    AccountLockedError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationAppError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_opaque_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole
from app.models.patient import Patient
from app.models.token import PasswordResetToken, RefreshToken
from app.models.user import User
from app.repositories.patient_repository import PatientRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest
from app.services.audit_service import AuditService
from app.utils.cpf_validator import is_valid_cpf

settings = get_settings()


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.patients = PatientRepository(db)
        self.audit = AuditService(db)

    def register_patient(self, payload: RegisterRequest, ip_address: str | None = None) -> User:
        if self.users.get_by_email(payload.email):
            raise ConflictError("E-mail já cadastrado.")

        if not is_valid_cpf(payload.cpf):
            raise ValidationAppError("CPF inválido.")

        cpf_digits = "".join(filter(str.isdigit, payload.cpf))
        if self.patients.get_by_cpf(cpf_digits):
            raise ConflictError("CPF já cadastrado.")

        user = User(
            email=payload.email.lower(),
            hashed_password=hash_password(payload.password),
            role=UserRole.PATIENT,
        )
        self.db.add(user)
        self.db.flush()

        patient = Patient(
            user_id=user.id,
            full_name=payload.full_name,
            cpf=cpf_digits,
            birth_date=payload.birth_date,
            sex=payload.sex,
            phone=payload.phone,
            email=payload.email,
            address_street=payload.address_street,
            address_number=payload.address_number,
            address_complement=payload.address_complement,
            address_neighborhood=payload.address_neighborhood,
            address_city=payload.address_city,
            address_state=payload.address_state.upper(),
            address_zip_code=payload.address_zip_code,
            insurance=payload.insurance,
            allergies=payload.allergies,
            observations=payload.observations,
        )
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(user)

        self.audit.log(user.id, "REGISTER", "User", user.id, ip_address=ip_address)
        return user

    def authenticate(self, email: str, password: str, ip_address: str | None = None) -> User:
        user = self.users.get_by_email(email)
        if user is None:
            raise UnauthorizedError("E-mail ou senha inválidos.")

        now = datetime.now(timezone.utc)
        locked_until = _ensure_timezone(user.locked_until) if user.locked_until else None
        if locked_until and locked_until > now:
            raise AccountLockedError(
                f"Conta bloqueada até {locked_until.isoformat()} devido a tentativas de login inválidas."
            )

        if not verify_password(password, user.hashed_password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.max_failed_login_attempts:
                user.locked_until = now + timedelta(minutes=settings.account_lockout_minutes)
                user.failed_login_attempts = 0
                self.users.update(user)
                self.audit.log(user.id, "ACCOUNT_LOCKED", "User", user.id, ip_address=ip_address)
                raise AccountLockedError(
                    "Conta bloqueada temporariamente devido a múltiplas tentativas de login inválidas."
                )
            self.users.update(user)
            self.audit.log(user.id, "LOGIN_FAILED", "User", user.id, ip_address=ip_address)
            raise UnauthorizedError("E-mail ou senha inválidos.")

        if not user.is_active:
            raise UnauthorizedError("Usuário inativo.")

        user.failed_login_attempts = 0
        user.locked_until = None
        self.users.update(user)
        self.audit.log(user.id, "LOGIN_SUCCESS", "User", user.id, ip_address=ip_address)
        return user

    def issue_tokens(self, user: User) -> tuple[str, str]:
        access_token = create_access_token(str(user.id), user.role.value)
        refresh_token, jti, expires_at = create_refresh_token(str(user.id), user.role.value)

        token_record = RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at)
        self.users.save_refresh_token(token_record)

        return access_token, refresh_token

    def refresh_access_token(self, refresh_token: str) -> str:
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise UnauthorizedError(str(exc)) from exc

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Token fornecido não é um refresh token.")

        token_record = self.users.get_refresh_token(payload["jti"])
        if token_record is None or token_record.revoked:
            raise UnauthorizedError("Refresh token inválido ou revogado.")

        now = datetime.now(timezone.utc)
        expires_at = _ensure_timezone(token_record.expires_at)
        if expires_at < now:
            raise UnauthorizedError("Refresh token expirado.")

        user = self.users.get_by_id(token_record.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Usuário inválido.")

        return create_access_token(str(user.id), user.role.value)

    def revoke_refresh_token(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise UnauthorizedError(str(exc)) from exc

        token_record = self.users.get_refresh_token(payload["jti"])
        if token_record is not None:
            self.users.revoke_refresh_token(token_record)

    def change_password(
        self, user: User, current_password: str, new_password: str, ip_address: str | None = None
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise UnauthorizedError("Senha atual incorreta.")

        user.hashed_password = hash_password(new_password)
        self.users.update(user)
        self.audit.log(user.id, "CHANGE_PASSWORD", "User", user.id, ip_address=ip_address)

    def request_password_reset(self, email: str, ip_address: str | None = None) -> str | None:
        user = self.users.get_by_email(email)
        if user is None:
            return None

        token_value = generate_opaque_token()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        )
        token_record = PasswordResetToken(user_id=user.id, token=token_value, expires_at=expires_at)
        self.users.save_password_reset_token(token_record)

        self.audit.log(user.id, "PASSWORD_RESET_REQUESTED", "User", user.id, ip_address=ip_address)
        return token_value

    def reset_password(self, token: str, new_password: str, ip_address: str | None = None) -> None:
        token_record = self.users.get_password_reset_token(token)
        if token_record is None or token_record.used:
            raise UnauthorizedError("Token de recuperação inválido.")

        now = datetime.now(timezone.utc)
        expires_at = _ensure_timezone(token_record.expires_at)
        if expires_at < now:
            raise UnauthorizedError("Token de recuperação expirado.")

        user = self.users.get_by_id(token_record.user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado.")

        user.hashed_password = hash_password(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        self.users.update(user)

        token_record.used = True
        self.db.commit()

        self.audit.log(user.id, "PASSWORD_RESET_COMPLETED", "User", user.id, ip_address=ip_address)


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
