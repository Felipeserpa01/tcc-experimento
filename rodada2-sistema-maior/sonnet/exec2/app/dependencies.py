"""Shared FastAPI dependencies: current user, role-based access control."""
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import JWTError, TokenType, decode_token
from app.database import get_db
from app.models.patient import Patient
from app.models.professional import Professional
from app.models.user import User
from app.repositories.patient_repository import PatientRepository
from app.repositories.professional_repository import ProfessionalRepository
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Token de autenticação não informado.")

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise UnauthorizedError("Token inválido ou expirado.")

    if payload.get("type") != TokenType.ACCESS.value:
        raise UnauthorizedError("Token informado não é um access token válido.")

    user_id = int(payload["sub"])
    user = UserRepository(db).get_by_id(user_id)
    if not user:
        raise UnauthorizedError("Usuário não encontrado.")
    if not user.is_active:
        raise ForbiddenError("Esta conta está desativada.")
    return user


def require_roles(*roles: UserRole):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise ForbiddenError("Você não tem permissão para executar esta ação.")
        return current_user

    return dependency


def get_current_patient(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Patient:
    if current_user.role != UserRole.PACIENTE:
        raise ForbiddenError("Apenas pacientes podem acessar este recurso.")
    patient = PatientRepository(db).get_by_user_id(current_user.id)
    if not patient:
        raise NotFoundError("Cadastro de paciente não encontrado para este usuário.")
    return patient


def get_current_professional(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Professional:
    professional = ProfessionalRepository(db).get_by_user_id(current_user.id)
    if not professional:
        raise NotFoundError("Cadastro de profissional não encontrado para este usuário.")
    return professional
