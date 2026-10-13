from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import verify_token
from app.repositories.user_repository import UserRepository
from app.models import UserRole

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    user_id = verify_token(token)

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user

def require_role(*roles: UserRole):
    def role_checker(current_user = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return role_checker
