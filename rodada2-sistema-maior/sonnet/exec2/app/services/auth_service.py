"""Authentication service: registration, login with lockout, tokens, password change/reset."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import (
    AccountLockedError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationAppError,
)
from app.core.security import (
    JWTError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserRegister
from app.services.audit_service import AuditService

settings = get_settings()


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)
        self.audit = AuditService(db)

    def register(self, data: UserRegister, ip_address: str | None = None) -> User:
        existing = self.repo.get_by_email(data.email)
        if existing:
            raise ConflictError("Já existe um usuário cadastrado com este e-mail.")

        user = User(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            role=data.role,
        )
        self.repo.create(user)
        self.db.commit()
        self.audit.log(user.id, "USER_REGISTER", "User", user.id, ip_address=ip_address)
        self.db.commit()
        return user

    def _is_locked(self, user: User) -> bool:
        if user.locked_until is None:
            return False
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        return locked_until > datetime.now(timezone.utc)

    def authenticate(self, email: str, password: str, ip_address: str | None = None) -> User:
        user = self.repo.get_by_email(email)
        if not user:
            self.audit.log(None, "LOGIN_FAILED", "User", details={"email": email}, ip_address=ip_address)
            self.db.commit()
            raise UnauthorizedError("E-mail ou senha inválidos.")

        if self._is_locked(user):
            self.audit.log(user.id, "LOGIN_BLOCKED", "User", user.id, ip_address=ip_address)
            self.db.commit()
            raise AccountLockedError(
                "Conta bloqueada temporariamente devido a múltiplas tentativas de login malsucedidas. "
                "Tente novamente mais tarde."
            )

        if not user.is_active:
            raise ForbiddenError("Esta conta está desativada.")

        if not verify_password(password, user.hashed_password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.max_failed_login_attempts:
                user.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.account_lockout_minutes
                )
                self.audit.log(user.id, "ACCOUNT_LOCKED", "User", user.id, ip_address=ip_address)
            self.repo.update(user)
            self.audit.log(user.id, "LOGIN_FAILED", "User", user.id, ip_address=ip_address)
            self.db.commit()
            raise UnauthorizedError("E-mail ou senha inválidos.")

        user.failed_login_attempts = 0
        user.locked_until = None
        self.repo.update(user)
        self.audit.log(user.id, "LOGIN_SUCCESS", "User", user.id, ip_address=ip_address)
        self.db.commit()
        return user

    def issue_tokens(self, user: User) -> tuple[str, str]:
        access = create_access_token(user.id, user.role.value)
        refresh = create_refresh_token(user.id, user.role.value)
        return access, refresh

    def refresh_access_token(self, refresh_token: str) -> str:
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise UnauthorizedError("Token de atualização inválido ou expirado.")

        if payload.get("type") != TokenType.REFRESH.value:
            raise UnauthorizedError("Token informado não é um refresh token válido.")

        user_id = int(payload["sub"])
        user = self.repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("Usuário não encontrado ou inativo.")

        return create_access_token(user.id, user.role.value)

    def change_password(
        self, user: User, current_password: str, new_password: str, ip_address: str | None = None
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise UnauthorizedError("Senha atual incorreta.")
        user.hashed_password = hash_password(new_password)
        user.must_change_password = False
        self.repo.update(user)
        self.audit.log(user.id, "PASSWORD_CHANGE", "User", user.id, ip_address=ip_address)
        self.db.commit()

    def request_password_reset(self, email: str, ip_address: str | None = None) -> str | None:
        """Generates a reset token. Returns the plain token (in production this would be emailed,
        never returned directly to the caller)."""
        user = self.repo.get_by_email(email)
        if not user:
            # Do not reveal whether the e-mail exists.
            return None
        plain_token, hashed_token = generate_reset_token()
        user.reset_token = hashed_token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        )
        self.repo.update(user)
        self.audit.log(user.id, "PASSWORD_RESET_REQUESTED", "User", user.id, ip_address=ip_address)
        self.db.commit()
        return plain_token

    def confirm_password_reset(self, token: str, new_password: str, ip_address: str | None = None) -> None:
        hashed = hash_reset_token(token)
        user = self.repo.get_by_reset_token(hashed)
        if not user:
            raise NotFoundError("Token de recuperação inválido.")

        expires = user.reset_token_expires
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if not expires or expires < datetime.now(timezone.utc):
            raise ValidationAppError("Token de recuperação expirado.")

        user.hashed_password = hash_password(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        user.failed_login_attempts = 0
        user.locked_until = None
        self.repo.update(user)
        self.audit.log(user.id, "PASSWORD_RESET_CONFIRMED", "User", user.id, ip_address=ip_address)
        self.db.commit()
