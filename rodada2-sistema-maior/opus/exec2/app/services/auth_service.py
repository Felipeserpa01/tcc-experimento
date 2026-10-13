"""Autenticação: registro, login com bloqueio por tentativas, tokens e senhas."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core import clock, security
from app.core.config import get_settings
from app.core.exceptions import AccountLockedError, AuthenticationError, ConflictError, PermissionDeniedError
from app.models.enums import Role
from app.models.user import PasswordResetToken, RefreshToken, User
from app.repositories.user_repository import (
    PasswordResetTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.schemas.auth import RegisterRequest, TokenResponse
from app.services.audit_service import AuditAction, AuditService
from app.services.notification_service import NotificationService
from app.services.patient_service import PatientService

INVALID_CREDENTIALS = "E-mail ou senha inválidos."


class AuthService:
    def __init__(self, db: Session, notifications: NotificationService) -> None:
        self.db = db
        self.settings = get_settings()
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)
        self.reset_tokens = PasswordResetTokenRepository(db)
        self.audit = AuditService(db)
        self.notifications = notifications

    # ------------------------------------------------------------------ registro
    def register_patient(self, data: RegisterRequest) -> User:
        if self.users.email_exists(data.email):
            raise ConflictError("Já existe um usuário cadastrado com este e-mail.")

        patient_service = PatientService(self.db)
        patient = patient_service.build_patient(data)
        user = self.users.add(
            User(
                email=data.email,
                full_name=data.full_name,
                hashed_password=security.hash_password(data.password),
                role=Role.PATIENT,
                password_changed_at=clock.now(),
            )
        )
        patient.user = user
        patient_service.patients.add(patient)
        self.audit.log(AuditAction.REGISTER, actor=user, entity_type="usuario", entity_id=user.id)
        self.db.commit()
        return user

    # ------------------------------------------------------------------ login
    def login(self, email: str, password: str) -> TokenResponse:
        now = clock.now()
        user = self.users.get_by_email(email)
        if user is None:
            security.simulate_password_check(password)
            self.audit.log(AuditAction.LOGIN_FAILED, actor_email=email, details={"motivo": "usuario_inexistente"})
            self.db.commit()
            raise AuthenticationError(INVALID_CREDENTIALS, code="credenciais_invalidas")

        if user.is_locked(now):
            self.audit.log(AuditAction.LOGIN_BLOCKED, actor=user, entity_type="usuario", entity_id=user.id)
            self.db.commit()
            raise self._locked_error(user.locked_until)  # type: ignore[arg-type]

        if user.locked_until is not None:  # bloqueio expirado: zera o contador
            user.locked_until = None
            user.failed_login_attempts = 0

        if not security.verify_password(password, user.hashed_password):
            self._register_failed_attempt(user, now)
            if user.is_locked(now):
                raise self._locked_error(user.locked_until)  # type: ignore[arg-type]
            raise AuthenticationError(INVALID_CREDENTIALS, code="credenciais_invalidas")

        if not user.is_active:
            self.audit.log(AuditAction.LOGIN_FAILED, actor=user, details={"motivo": "usuario_inativo"})
            self.db.commit()
            raise PermissionDeniedError("Conta desativada. Procure a administração da clínica.", code="conta_inativa")

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now
        tokens, _ = self._issue_tokens(user)
        self.audit.log(AuditAction.LOGIN_SUCCESS, actor=user, entity_type="usuario", entity_id=user.id)
        self.db.commit()
        return tokens

    def _register_failed_attempt(self, user: User, now: datetime) -> None:
        user.failed_login_attempts += 1
        remaining = self.settings.max_failed_login_attempts - user.failed_login_attempts
        self.audit.log(
            AuditAction.LOGIN_FAILED,
            actor=user,
            entity_type="usuario",
            entity_id=user.id,
            details={"motivo": "senha_incorreta", "tentativas": user.failed_login_attempts},
        )
        if remaining <= 0:
            user.locked_until = now + timedelta(minutes=self.settings.account_lock_minutes)
            self.audit.log(
                AuditAction.ACCOUNT_LOCKED,
                actor=user,
                entity_type="usuario",
                entity_id=user.id,
                details={"bloqueado_ate": user.locked_until.isoformat()},
            )
        self.db.commit()

    @staticmethod
    def _locked_error(locked_until: datetime) -> AccountLockedError:
        return AccountLockedError(
            "Conta temporariamente bloqueada por excesso de tentativas de login. "
            f"Tente novamente após {locked_until.strftime('%d/%m/%Y %H:%M')}.",
            details={"locked_until": locked_until.isoformat()},
        )

    # ------------------------------------------------------------------ tokens
    def _issue_tokens(self, user: User) -> tuple[TokenResponse, str]:
        """Emite o par de tokens e retorna também o ``jti`` do novo refresh token."""
        access = security.create_access_token(user.id, user.role.value, user.token_version)
        refresh = security.create_refresh_token(user.id, user.token_version)
        self.refresh_tokens.add(
            RefreshToken(
                jti=refresh.jti,
                user_id=user.id,
                # Mesma fonte de tempo usada na verificação em ``refresh`` (relógio da clínica).
                expires_at=clock.now() + timedelta(seconds=refresh.expires_in),
            )
        )
        response = TokenResponse(
            access_token=access.token,
            refresh_token=refresh.token,
            expires_in=access.expires_in,
            refresh_expires_in=refresh.expires_in,
        )
        return response, refresh.jti

    def refresh(self, refresh_token: str) -> TokenResponse:
        """Rotação de refresh token: cada token só pode ser usado uma vez.

        A reutilização de um token já rotacionado indica possível roubo; nesse caso
        todas as sessões do usuário são revogadas.
        """
        payload = security.decode_token(refresh_token, security.REFRESH_TOKEN_TYPE)
        now = clock.now()
        stored = self.refresh_tokens.get_by_jti(payload["jti"])
        if stored is None or stored.user_id != payload["sub"]:
            raise AuthenticationError("Refresh token inválido.", code="token_invalido")

        if stored.revoked_at is not None:
            if stored.replaced_by_jti is not None:  # token já rotacionado sendo reapresentado
                self.refresh_tokens.revoke_all_for_user(stored.user_id, now)
                self.audit.log(
                    AuditAction.REFRESH_REUSE, actor=stored.user, entity_type="usuario", entity_id=stored.user_id
                )
                self.db.commit()
                raise AuthenticationError(
                    "Refresh token já utilizado. Por segurança, todas as sessões foram encerradas.",
                    code="token_reutilizado",
                )
            raise AuthenticationError("Refresh token revogado. Faça login novamente.", code="token_revogado")

        user = stored.user
        if stored.expires_at <= now:
            raise AuthenticationError("Refresh token expirado.", code="token_expirado")
        if not user.is_active or payload.get("ver") != user.token_version:
            raise AuthenticationError("Sessão inválida. Faça login novamente.", code="token_invalido")

        tokens, new_jti = self._issue_tokens(user)
        stored.revoked_at = now
        stored.replaced_by_jti = new_jti
        self.db.commit()
        return tokens

    def logout(self, user: User, refresh_token: str) -> None:
        payload = security.decode_token(refresh_token, security.REFRESH_TOKEN_TYPE)
        stored = self.refresh_tokens.get_by_jti(payload["jti"])
        if stored is None or stored.user_id != user.id:
            raise AuthenticationError("Refresh token inválido.", code="token_invalido")
        if stored.revoked_at is None:
            stored.revoked_at = clock.now()
        self.audit.log(AuditAction.LOGOUT, actor=user, entity_type="usuario", entity_id=user.id)
        self.db.commit()

    # ------------------------------------------------------------------ senhas
    def _set_password(self, user: User, new_password: str) -> None:
        now = clock.now()
        user.hashed_password = security.hash_password(new_password)
        user.password_changed_at = now
        user.token_version += 1  # invalida access/refresh tokens emitidos antes
        user.failed_login_attempts = 0
        user.locked_until = None
        self.refresh_tokens.revoke_all_for_user(user.id, now)

    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not security.verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Senha atual incorreta.", code="senha_incorreta")
        self._set_password(user, new_password)
        self.audit.log(AuditAction.PASSWORD_CHANGED, actor=user, entity_type="usuario", entity_id=user.id)
        self.db.commit()

    def request_password_reset(self, email: str) -> None:
        """Sempre responde da mesma forma (não revela se o e-mail existe)."""
        user = self.users.get_by_email(email)
        if user is None or not user.is_active:
            self.audit.log(AuditAction.PASSWORD_RESET_REQUESTED, actor_email=email, details={"enviado": False})
            self.db.commit()
            return

        now = clock.now()
        self.reset_tokens.invalidate_pending_for_user(user.id, now)
        token = security.generate_opaque_token()
        minutes = self.settings.password_reset_token_expire_minutes
        self.reset_tokens.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=security.hash_opaque_token(token),
                expires_at=now + timedelta(minutes=minutes),
            )
        )
        self.notifications.queue_email(
            user.email,
            "Recuperação de senha",
            f"Olá, {user.full_name}.\n\nUse o código abaixo para redefinir sua senha "
            f"(válido por {minutes} minutos):\n\n{token}\n\n"
            "Se você não solicitou a recuperação, ignore esta mensagem.",
        )
        self.audit.log(
            AuditAction.PASSWORD_RESET_REQUESTED,
            actor=user,
            entity_type="usuario",
            entity_id=user.id,
            details={"enviado": True},
        )
        self.db.commit()

    def reset_password(self, token: str, new_password: str) -> None:
        now = clock.now()
        stored = self.reset_tokens.get_by_hash(security.hash_opaque_token(token))
        if stored is None or stored.used_at is not None or stored.expires_at <= now:
            raise AuthenticationError("Token de recuperação inválido ou expirado.", code="token_invalido")
        user = stored.user
        if not user.is_active:
            raise AuthenticationError("Token de recuperação inválido ou expirado.", code="token_invalido")
        stored.used_at = now
        self._set_password(user, new_password)
        self.audit.log(AuditAction.PASSWORD_RESET, actor=user, entity_type="usuario", entity_id=user.id)
        self.db.commit()

    # ------------------------------------------------------------------ usuário corrente
    def authenticate_access_token(self, token: str) -> User:
        payload = security.decode_token(token, security.ACCESS_TOKEN_TYPE)
        user = self.users.get(payload["sub"])
        if user is None or not user.is_active:
            raise AuthenticationError("Usuário inexistente ou inativo.", code="token_invalido")
        if payload.get("ver") != user.token_version:
            raise AuthenticationError("Sessão expirada. Faça login novamente.", code="token_revogado")
        return user
