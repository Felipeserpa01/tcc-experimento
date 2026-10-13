"""Autenticacao, sessoes, politica de senha e bloqueio de conta."""

from __future__ import annotations

import math
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.context import get_request_context
from app.core.datetime_utils import now
from app.core.exceptions import (
    AccountInactiveError,
    AccountLockedError,
    AuthenticationError,
    BusinessRuleError,
    DuplicateResourceError,
    InvalidTokenError,
    NotFoundError,
    ValidationFailedError,
)
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)
from app.models.enums import AuditStatus, Gender, NotificationType, UserRole
from app.models.patient import Patient
from app.models.user import PasswordResetToken, RefreshToken, User
from app.repositories.patient_repository import PatientRepository
from app.repositories.user_repository import (
    PasswordResetTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.schemas.auth import RegisterRequest
from app.services.audit_service import AuditAction, AuditService
from app.services.notification_service import NotificationService
from app.utils.validators import normalize_cpf, normalize_phone

settings = get_settings()

#: Mensagem unica para credenciais invalidas (nao revela se o email existe).
GENERIC_AUTH_MESSAGE = "Email ou senha invalidos."


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.patients = PatientRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)
        self.reset_tokens = PasswordResetTokenRepository(db)
        self.audit = AuditService(db)
        self.notifications = NotificationService(db)

    # ------------------------------------------------------------------
    # Registro publico
    # ------------------------------------------------------------------
    def register_patient(self, payload: RegisterRequest) -> User:
        email = payload.email.strip().lower()
        if self.users.email_taken(email):
            raise DuplicateResourceError("Ja existe um usuario com este email.")

        try:
            cpf = normalize_cpf(payload.cpf)
            phone = normalize_phone(payload.phone)
        except ValueError as exc:
            raise ValidationFailedError(str(exc)) from exc

        if self.patients.cpf_taken(cpf):
            raise DuplicateResourceError("Ja existe um paciente cadastrado com este CPF.")

        user = User(
            email=email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role=UserRole.PATIENT,
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()

        patient = Patient(
            user_id=user.id,
            full_name=payload.full_name,
            cpf=cpf,
            birth_date=payload.birth_date,
            gender=Gender.NOT_INFORMED,
            phone=phone,
            email=email,
            address_street="A informar",
            address_number="S/N",
            address_district="A informar",
            address_city="A informar",
            address_state="SP",
            address_zip_code="00000000",
        )
        self.db.add(patient)
        self.db.flush()

        self.audit.record(
            action=AuditAction.REGISTER,
            actor=user,
            resource_type="user",
            resource_id=user.id,
            description=f"Auto cadastro de paciente '{user.email}'.",
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    def authenticate(self, email: str, password: str) -> tuple[User, str, str, int]:
        normalized_email = (email or "").strip().lower()
        user = self.users.get_by_email(normalized_email)

        if user is None:
            self.audit.record(
                action=AuditAction.LOGIN_FAILED,
                actor_email=normalized_email,
                status=AuditStatus.FAILURE,
                description="Tentativa de login com email inexistente.",
            )
            self.db.commit()
            raise AuthenticationError(GENERIC_AUTH_MESSAGE)

        if user.is_locked:
            remaining = max(1, math.ceil((user.locked_until - now()).total_seconds() / 60))
            self.audit.record(
                action=AuditAction.LOGIN_BLOCKED,
                actor=user,
                status=AuditStatus.FAILURE,
                description="Tentativa de login em conta bloqueada.",
            )
            self.db.commit()
            raise AccountLockedError(
                f"Conta bloqueada por excesso de tentativas. Tente novamente em {remaining} minuto(s)."
            )

        if not verify_password(password, user.hashed_password):
            locked = user.register_failed_login(
                settings.max_login_attempts, settings.account_lockout_minutes
            )
            remaining_attempts = max(0, settings.max_login_attempts - user.failed_login_attempts)
            self.audit.record(
                action=AuditAction.LOGIN_FAILED,
                actor=user,
                status=AuditStatus.FAILURE,
                description=(
                    f"Senha incorreta. Tentativas restantes: {remaining_attempts}."
                ),
                extra={"failed_attempts": user.failed_login_attempts},
            )
            if locked:
                self.audit.record(
                    action=AuditAction.ACCOUNT_LOCKED,
                    actor=user,
                    status=AuditStatus.FAILURE,
                    description=(
                        f"Conta bloqueada por {settings.account_lockout_minutes} minutos apos "
                        f"{settings.max_login_attempts} tentativas malsucedidas."
                    ),
                )
                self.db.commit()
                raise AccountLockedError(
                    "Conta bloqueada por excesso de tentativas de login. "
                    f"Tente novamente em {settings.account_lockout_minutes} minuto(s)."
                )
            self.db.commit()
            raise AuthenticationError(GENERIC_AUTH_MESSAGE)

        if not user.is_active:
            self.audit.record(
                action=AuditAction.LOGIN_FAILED,
                actor=user,
                status=AuditStatus.FAILURE,
                description="Tentativa de login em conta desativada.",
            )
            self.db.commit()
            raise AccountInactiveError("Conta desativada. Procure o administrador do sistema.")

        user.register_successful_login()
        access, refresh = self._issue_tokens(user)

        self.audit.record(
            action=AuditAction.LOGIN_SUCCESS,
            actor=user,
            resource_type="user",
            resource_id=user.id,
            description="Login realizado com sucesso.",
        )
        self.db.commit()
        return user, access.token, refresh.token, access.expires_in

    def _issue_tokens(self, user: User):
        context = get_request_context()
        access = create_access_token(user.id, user.role.value, extra_claims={"email": user.email})
        refresh = create_refresh_token(user.id, user.role.value)
        self.db.add(
            RefreshToken(
                user_id=user.id,
                jti=refresh.jti,
                token_hash=hash_token(refresh.token),
                expires_at=refresh.expires_at,
                user_agent=(context.user_agent or "")[:255] or None,
                ip_address=context.ip_address,
            )
        )
        self.db.flush()
        return access, refresh

    # ------------------------------------------------------------------
    # Refresh com rotacao
    # ------------------------------------------------------------------
    def refresh_session(self, refresh_token: str) -> tuple[User, str, str, int]:
        payload = decode_token(refresh_token, expected_type=TOKEN_TYPE_REFRESH)
        stored = self.refresh_tokens.get_by_jti(payload["jti"])

        if stored is None:
            raise InvalidTokenError("Refresh token desconhecido.")

        if not stored.is_active:
            # Reuso de token revogado: encerra todas as sessoes por seguranca.
            self.refresh_tokens.revoke_all_for_user(stored.user_id)
            self.audit.record(
                action=AuditAction.TOKEN_REUSE_DETECTED,
                actor=stored.user,
                status=AuditStatus.FAILURE,
                resource_type="refresh_token",
                resource_id=stored.id,
                description="Reuso de refresh token revogado/expirado. Sessoes encerradas.",
            )
            self.db.commit()
            raise InvalidTokenError("Refresh token invalido ou ja utilizado.")

        if stored.token_hash != hash_token(refresh_token):
            raise InvalidTokenError("Refresh token invalido.")

        user = self.users.get(stored.user_id)
        if user is None:
            raise InvalidTokenError("Usuario do token nao existe mais.")
        if not user.is_active:
            raise AccountInactiveError("Conta desativada.")
        if user.is_locked:
            raise AccountLockedError()

        access, new_refresh = self._issue_tokens(user)
        stored.revoke(replaced_by=new_refresh.jti)

        self.audit.record(
            action=AuditAction.TOKEN_REFRESHED,
            actor=user,
            resource_type="user",
            resource_id=user.id,
            description="Access token renovado (rotacao de refresh token).",
        )
        self.db.commit()
        return user, access.token, new_refresh.token, access.expires_in

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------
    def logout(self, user: User, refresh_token: str | None, all_sessions: bool = False) -> int:
        revoked = 0
        if all_sessions or not refresh_token:
            revoked = self.refresh_tokens.revoke_all_for_user(user.id)
        else:
            stored = self.refresh_tokens.get_active_by_hash(hash_token(refresh_token))
            if stored is not None and stored.user_id == user.id:
                stored.revoke()
                revoked = 1

        self.audit.record(
            action=AuditAction.LOGOUT,
            actor=user,
            resource_type="user",
            resource_id=user.id,
            description=f"Logout realizado ({revoked} sessao(oes) encerrada(s)).",
        )
        self.db.commit()
        return revoked

    # ------------------------------------------------------------------
    # Troca de senha
    # ------------------------------------------------------------------
    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.hashed_password):
            self.audit.record(
                action=AuditAction.PASSWORD_CHANGED,
                actor=user,
                status=AuditStatus.FAILURE,
                resource_type="user",
                resource_id=user.id,
                description="Troca de senha recusada: senha atual incorreta.",
            )
            self.db.commit()
            raise AuthenticationError("Senha atual incorreta.")

        if current_password == new_password:
            raise BusinessRuleError("A nova senha deve ser diferente da senha atual.")

        validate_password_strength(new_password)
        user.hashed_password = hash_password(new_password)
        user.password_changed_at = now()
        self.refresh_tokens.revoke_all_for_user(user.id)
        self.reset_tokens.invalidate_for_user(user.id)

        self.audit.record(
            action=AuditAction.PASSWORD_CHANGED,
            actor=user,
            resource_type="user",
            resource_id=user.id,
            description="Senha alterada pelo proprio usuario. Sessoes encerradas.",
        )
        self.db.commit()

    # ------------------------------------------------------------------
    # Recuperacao de senha
    # ------------------------------------------------------------------
    def request_password_recovery(self, email: str) -> tuple[str | None, PasswordResetToken | None]:
        """Sempre responde de forma neutra para nao revelar emails cadastrados."""
        normalized = (email or "").strip().lower()
        user = self.users.get_by_email(normalized)

        if user is None or not user.is_active:
            self.audit.record(
                action=AuditAction.PASSWORD_RECOVERY_REQUESTED,
                actor=user,
                actor_email=normalized,
                status=AuditStatus.FAILURE,
                description="Recuperacao solicitada para email inexistente ou inativo.",
            )
            self.db.commit()
            return None, None

        self.reset_tokens.invalidate_for_user(user.id)
        raw_token = generate_opaque_token()
        reset = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=now() + timedelta(minutes=settings.password_reset_token_expire_minutes),
        )
        self.db.add(reset)
        self.db.flush()

        self.notifications.notify(
            user_id=user.id,
            notification_type=NotificationType.PASSWORD_RECOVERY,
            title="Recuperacao de senha",
            message=(
                "Recebemos uma solicitacao de recuperacao de senha. "
                f"O link e valido por {settings.password_reset_token_expire_minutes} minutos."
            ),
            resource_type="user",
            resource_id=user.id,
        )
        self.audit.record(
            action=AuditAction.PASSWORD_RECOVERY_REQUESTED,
            actor=user,
            resource_type="user",
            resource_id=user.id,
            description="Token de recuperacao de senha gerado.",
        )
        self.db.commit()
        return raw_token, reset

    def reset_password(self, token: str, new_password: str) -> User:
        stored = self.reset_tokens.get_usable(hash_token(token))
        if stored is None:
            raise InvalidTokenError("Token de recuperacao invalido, expirado ou ja utilizado.")

        user = self.users.get(stored.user_id)
        if user is None:
            raise NotFoundError("Usuario nao encontrado.")
        if not user.is_active:
            raise AccountInactiveError("Conta desativada.")

        if verify_password(new_password, user.hashed_password):
            raise BusinessRuleError("A nova senha deve ser diferente da senha anterior.")

        validate_password_strength(new_password)
        user.hashed_password = hash_password(new_password)
        user.password_changed_at = now()
        user.failed_login_attempts = 0
        user.locked_until = None
        stored.used_at = now()
        self.refresh_tokens.revoke_all_for_user(user.id)

        self.audit.record(
            action=AuditAction.PASSWORD_RESET,
            actor=user,
            resource_type="user",
            resource_id=user.id,
            description="Senha redefinida via token de recuperacao.",
        )
        self.db.commit()
        return user
