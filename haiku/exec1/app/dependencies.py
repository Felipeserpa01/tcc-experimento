from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import decode_token
from app.models import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security), db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
        )

    return user


async def get_current_librarian(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_librarian:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas bibliotecários podem acessar este recurso",
        )
    return current_user
