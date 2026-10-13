from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models import User, AuditLog, UserRole
from app.schemas import UserCreate, LoginRequest, PasswordChangeRequest
from app.security import hash_password, verify_password, create_access_token, create_refresh_token, verify_token
from app.repositories.user_repository import UserRepository

LOCKOUT_DURATION_MINUTES = 15
MAX_LOGIN_ATTEMPTS = 5

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def register(self, user_data: UserCreate) -> dict:
        if self.user_repo.get_by_email(user_data.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        if self.user_repo.get_by_username(user_data.username):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            role=user_data.role,
            hashed_password=hash_password(user_data.password)
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        self._log_audit(None, "USER_REGISTERED", "User", user.id, f"User {user.username} registered")

        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role
        }

    def login(self, login_data: LoginRequest) -> dict:
        user = self.user_repo.get_by_username(login_data.username)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if user.locked_until and user.locked_until > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account locked. Try again later."
            )

        if not verify_password(login_data.password, user.hashed_password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            self.db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        user.failed_login_attempts = 0
        user.locked_until = None
        self.db.commit()

        access_token = create_access_token({"sub": user.id, "role": user.role.value})
        refresh_token = create_refresh_token({"sub": user.id})

        self._log_audit(user.id, "LOGIN", "User", user.id, f"User {user.username} logged in")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value
            }
        }

    def refresh_access_token(self, refresh_token: str) -> dict:
        user_id = verify_token(refresh_token)
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

        access_token = create_access_token({"sub": user.id, "role": user.role.value})
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    def change_password(self, user_id: int, password_change: PasswordChangeRequest) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if not verify_password(password_change.old_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")

        user.hashed_password = hash_password(password_change.new_password)
        self.db.commit()

        self._log_audit(user_id, "PASSWORD_CHANGED", "User", user_id, "User changed password")

        return {"message": "Password changed successfully"}

    def reset_password(self, email: str, new_password: str) -> dict:
        user = self.user_repo.get_by_email(email)
        if not user:
            return {"message": "If email exists, password reset link will be sent"}

        user.hashed_password = hash_password(new_password)
        self.db.commit()

        self._log_audit(user_id, "PASSWORD_RESET", "User", user.id, "User password reset")

        return {"message": "Password reset successfully"}

    def _log_audit(self, user_id, action: str, entity_type: str, entity_id: int, details: str = None):
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details
        )
        self.db.add(audit_log)
        self.db.commit()
