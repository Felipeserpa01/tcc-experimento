"""Administração de usuários do sistema."""

from sqlalchemy.orm import Session

from app.core import clock, security
from app.core.config import get_settings
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.pagination import PageParams, PageResult, SortParams
from app.models.enums import ProfessionalType, Role
from app.models.user import User
from app.repositories.patient_repository import PatientRepository
from app.repositories.professional_repository import ProfessionalRepository
from app.repositories.user_repository import RefreshTokenRepository, UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_service import AuditAction, AuditService
from app.utils.validators import validate_password_strength


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)
        self.patients = PatientRepository(db)
        self.professionals = ProfessionalRepository(db)
        self.audit = AuditService(db)

    def get(self, user_id: int) -> User:
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado.")
        return user

    def search(
        self, page: PageParams, sort: SortParams, *, role: Role | None, is_active: bool | None, query: str | None
    ) -> PageResult[User]:
        return self.users.search(page, sort, role=role, is_active=is_active, query=query)

    def create(self, actor: User, data: UserCreate) -> User:
        if self.users.email_exists(data.email):
            raise ConflictError("Já existe um usuário cadastrado com este e-mail.")

        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=security.hash_password(data.password),
            role=data.role,
            password_changed_at=clock.now(),
        )

        if data.patient_id is not None:
            patient = self.patients.get(data.patient_id)
            if patient is None:
                raise NotFoundError("Paciente não encontrado.")
            if patient.user_id is not None:
                raise ConflictError("Este paciente já possui um usuário vinculado.")
            if not patient.is_active:
                raise BusinessRuleError("Não é possível criar acesso para um paciente inativo.")
            self.users.add(user)
            patient.user = user

        elif data.professional_id is not None:
            professional = self.professionals.get(data.professional_id)
            if professional is None:
                raise NotFoundError("Profissional não encontrado.")
            if professional.user_id is not None:
                raise ConflictError("Este profissional já possui um usuário vinculado.")
            expected = ProfessionalType.DOCTOR if data.role == Role.DOCTOR else ProfessionalType.NURSE
            if professional.professional_type != expected:
                raise BusinessRuleError("O perfil do usuário não corresponde ao tipo do profissional.")
            if not professional.is_active:
                raise BusinessRuleError("Não é possível criar acesso para um profissional inativo.")
            self.users.add(user)
            professional.user = user
        else:
            self.users.add(user)

        self.db.flush()
        self.audit.log(
            AuditAction.USER_CREATED,
            actor=actor,
            entity_type="usuario",
            entity_id=user.id,
            details={"perfil": data.role.value, "email": data.email},
        )
        self.db.commit()
        return user

    def update(self, actor: User, user_id: int, data: UserUpdate) -> User:
        user = self.get(user_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            raise BusinessRuleError("Nenhum campo informado para atualização.")
        if "email" in changes and self.users.email_exists(changes["email"], exclude_id=user.id):
            raise ConflictError("Já existe um usuário cadastrado com este e-mail.")
        if changes.get("is_active") is False:
            if user.id == actor.id:
                raise BusinessRuleError("Você não pode desativar a sua própria conta.")
            if user.is_active:
                user.token_version += 1  # derruba sessões ativas
                self.refresh_tokens.revoke_all_for_user(user.id, clock.now())

        for field, value in changes.items():
            setattr(user, field, value)
        self.audit.log(
            AuditAction.USER_UPDATED,
            actor=actor,
            entity_type="usuario",
            entity_id=user.id,
            details={"campos": sorted(changes)},
        )
        self.db.commit()
        return user

    def unlock(self, actor: User, user_id: int) -> User:
        user = self.get(user_id)
        user.failed_login_attempts = 0
        user.locked_until = None
        self.audit.log(AuditAction.USER_UNLOCKED, actor=actor, entity_type="usuario", entity_id=user.id)
        self.db.commit()
        return user

    def create_admin(self, email: str, full_name: str, password: str, origin: str) -> User:
        """Cria um administrador fora do fluxo HTTP (inicialização ou linha de comando)."""
        validate_password_strength(password)
        if self.users.email_exists(email):
            raise ConflictError("Já existe um usuário cadastrado com este e-mail.")
        admin = self.users.add(
            User(
                email=email.lower(),
                full_name=full_name,
                hashed_password=security.hash_password(password),
                role=Role.ADMIN,
                password_changed_at=clock.now(),
            )
        )
        self.audit.log(
            AuditAction.USER_CREATED,
            entity_type="usuario",
            entity_id=admin.id,
            details={"perfil": Role.ADMIN.value, "origem": origin},
        )
        self.db.commit()
        return admin

    def ensure_initial_admin(self) -> User | None:
        """Cria o administrador inicial definido por variáveis de ambiente, se ainda não houver nenhum."""
        settings = get_settings()
        if not settings.initial_admin_email or not settings.initial_admin_password:
            return None
        if self.users.admin_exists():
            return None
        return self.create_admin(
            settings.initial_admin_email, settings.initial_admin_name, settings.initial_admin_password, "inicializacao"
        )
