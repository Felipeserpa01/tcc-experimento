from datetime import datetime, timedelta
import secrets
import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token, hash_token
)
from app.core.exceptions import (
    UnauthorizedError, ConflictError, NotFoundError,
    AccountLockedError, ValidationError
)
from app.core.enums import Role, AuditAction
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.password_reset_repository import PasswordResetTokenRepository
from app.services.audit_service import AuditService
from app.utils.validators import validate_password_strength

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.refresh_token_repo = RefreshTokenRepository(db)
        self.password_reset_repo = PasswordResetTokenRepository(db)
        self.audit_service = AuditService(db)

    def register(self, email: str, password: str, full_name: str) -> User:
        # Check if user already exists
        existing = self.user_repo.get_by_email(email)
        if existing:
            raise ConflictError(f"Email {email} already registered")

        # Validate password strength
        if not validate_password_strength(password):
            raise ValidationError(
                "Password must be at least 8 characters and contain letters, numbers, and symbols"
            )

        # Create new user (patient by default)
        user = self.user_repo.create({
            "email": email,
            "hashed_password": hash_password(password),
            "full_name": full_name,
            "role": Role.PATIENT,
            "is_active": True
        })

        self.audit_service.log(
            action=AuditAction.PATIENT_CREATED,
            user_id=user.id,
            entity_type="User",
            entity_id=user.id
        )

        return user

    def login(self, email: str, password: str) -> dict:
        user = self.user_repo.get_by_email(email)

        if not user:
            self.audit_service.log(
                action=AuditAction.LOGIN_FAILED,
                details={"reason": "user_not_found", "email": email}
            )
            raise UnauthorizedError("Invalid email or password")

        # Check if account is locked
        if user.is_locked():
            self.audit_service.log(
                action=AuditAction.LOGIN_FAILED,
                user_id=user.id,
                details={"reason": "account_locked"}
            )
            raise AccountLockedError(f"Account locked until {user.locked_until}")

        # Verify password
        if not verify_password(password, user.hashed_password):
            user.failed_login_attempts += 1

            if user.failed_login_attempts >= settings.max_login_attempts:
                user.locked_until = datetime.utcnow() + timedelta(
                    minutes=settings.lockout_duration_minutes
                )
                self.audit_service.log(
                    action=AuditAction.LOGIN_LOCKED,
                    user_id=user.id,
                    details={"reason": "max_attempts_exceeded"}
                )

            self.db.add(user)
            self.db.commit()

            self.audit_service.log(
                action=AuditAction.LOGIN_FAILED,
                user_id=user.id,
                details={"reason": "invalid_password"}
            )
            raise UnauthorizedError("Invalid email or password")

        # Reset login attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        self.db.add(user)
        self.db.commit()

        # Generate tokens
        access_token = create_access_token(str(user.id), user.role)
        refresh_token = create_refresh_token(str(user.id))

        # Store refresh token hash
        token_hash = hash_token(refresh_token)
        expires_at = datetime.utcnow() + timedelta(
            days=settings.refresh_token_expire_days
        )
        self.refresh_token_repo.create({
            "user_id": user.id,
            "token_hash": token_hash,
            "expires_at": expires_at
        })

        self.audit_service.log(
            action=AuditAction.LOGIN_SUCCESS,
            user_id=user.id
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user.id,
            "role": user.role
        }

    def refresh_access_token(self, refresh_token: str) -> dict:
        # Decode token
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid refresh token")

        user_id = int(payload["sub"])

        # Check if token exists and is not revoked
        token_hash = hash_token(refresh_token)
        stored_token = self.refresh_token_repo.get_by_token_hash(token_hash)

        if not stored_token or stored_token.revoked:
            raise UnauthorizedError("Refresh token has been revoked")

        if datetime.utcnow() > stored_token.expires_at:
            raise UnauthorizedError("Refresh token has expired")

        # Get user
        user = self.user_repo.get(user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")

        # Generate new access token and refresh token
        new_access_token = create_access_token(str(user.id), user.role)
        new_refresh_token = create_refresh_token(str(user.id))

        # Revoke old token and store new one
        stored_token.revoked = True
        self.db.add(stored_token)

        new_token_hash = hash_token(new_refresh_token)
        new_expires_at = datetime.utcnow() + timedelta(
            days=settings.refresh_token_expire_days
        )
        self.refresh_token_repo.create({
            "user_id": user.id,
            "token_hash": new_token_hash,
            "expires_at": new_expires_at
        })

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }

    def logout(self, user_id: int):
        # Revoke all refresh tokens for this user
        self.refresh_token_repo.revoke_user_tokens(user_id)
        self.audit_service.log(
            action=AuditAction.LOGOUT,
            user_id=user_id
        )

    def request_password_reset(self, email: str) -> str:
        user = self.user_repo.get_by_email(email)

        # Always return success even if user doesn't exist (security best practice)
        if not user:
            return None

        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        token_hash = hash_token(reset_token)
        expires_at = datetime.utcnow() + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        )

        self.password_reset_repo.create({
            "user_id": user.id,
            "token_hash": token_hash,
            "expires_at": expires_at
        })

        logger.info(f"Password reset token generated for user {user.id}: {reset_token}")

        self.audit_service.log(
            action=AuditAction.PASSWORD_RESET,
            user_id=user.id,
            details={"action": "reset_requested"}
        )

        return reset_token

    def confirm_password_reset(self, token: str, new_password: str) -> User:
        # Validate password strength
        if not validate_password_strength(new_password):
            raise ValidationError(
                "Password must be at least 8 characters and contain letters, numbers, and symbols"
            )

        # Find token
        token_hash = hash_token(token)
        reset_token = self.password_reset_repo.get_by_token_hash(token_hash)

        if not reset_token or reset_token.used:
            raise UnauthorizedError("Invalid or already used reset token")

        if datetime.utcnow() > reset_token.expires_at:
            raise UnauthorizedError("Reset token has expired")

        # Update user password
        user = self.user_repo.get(reset_token.user_id)
        user.hashed_password = hash_password(new_password)
        self.db.add(user)
        self.db.commit()

        # Mark token as used
        reset_token.used = True
        self.db.add(reset_token)
        self.db.commit()

        # Revoke all existing refresh tokens
        self.refresh_token_repo.revoke_user_tokens(user.id)

        self.audit_service.log(
            action=AuditAction.PASSWORD_CHANGED,
            user_id=user.id
        )

        return user

    def change_password(self, user_id: int, old_password: str, new_password: str) -> User:
        user = self.user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found")

        # Verify old password
        if not verify_password(old_password, user.hashed_password):
            raise UnauthorizedError("Invalid current password")

        # Validate new password strength
        if not validate_password_strength(new_password):
            raise ValidationError(
                "Password must be at least 8 characters and contain letters, numbers, and symbols"
            )

        # Update password
        user.hashed_password = hash_password(new_password)
        self.db.add(user)
        self.db.commit()

        # Revoke all refresh tokens
        self.refresh_token_repo.revoke_user_tokens(user.id)

        self.audit_service.log(
            action=AuditAction.PASSWORD_CHANGED,
            user_id=user.id
        )

        return user
