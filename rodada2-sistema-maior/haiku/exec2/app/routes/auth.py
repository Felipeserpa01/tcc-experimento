from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import UserRole
from app.schemas import UserCreate, TokenResponse, LoginRequest, PasswordChangeRequest, PasswordResetRequest, RefreshTokenRequest
from app.services.auth_service import AuthService

router = APIRouter()

@router.post("/register", response_model=dict)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.register(user_data)

@router.post("/login", response_model=dict)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.login(login_data)

@router.post("/refresh", response_model=dict)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.refresh_access_token(request.refresh_token)

@router.post("/change-password", response_model=dict)
def change_password(
    password_change: PasswordChangeRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    return service.change_password(current_user.id, password_change)

@router.post("/reset-password", response_model=dict)
def reset_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.reset_password(request.email, "TempPassword123!")

@router.get("/me", response_model=dict)
def get_current_user_info(current_user = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role.value
    }
