"""Gestão de convênios."""

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.pagination import PageParams, PageResult, SortParams
from app.models.patient import HealthInsurance
from app.models.user import User
from app.repositories.patient_repository import InsuranceRepository
from app.schemas.insurance import InsuranceCreate, InsuranceUpdate
from app.services.audit_service import AuditAction, AuditService


class InsuranceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = InsuranceRepository(db)
        self.audit = AuditService(db)

    def get(self, insurance_id: int) -> HealthInsurance:
        insurance = self.repo.get(insurance_id)
        if insurance is None:
            raise NotFoundError("Convênio não encontrado.")
        return insurance

    def search(
        self, page: PageParams, sort: SortParams, *, name: str | None, is_active: bool | None
    ) -> PageResult[HealthInsurance]:
        return self.repo.search(page, sort, name=name, is_active=is_active)

    def create(self, actor: User, data: InsuranceCreate) -> HealthInsurance:
        if self.repo.name_exists(data.name):
            raise ConflictError("Já existe um convênio com este nome.")
        if data.ans_code and self.repo.ans_code_exists(data.ans_code):
            raise ConflictError("Já existe um convênio com este registro ANS.")
        insurance = self.repo.add(HealthInsurance(**data.model_dump()))
        self.audit.log(
            AuditAction.INSURANCE_CREATED,
            actor=actor,
            entity_type="convenio",
            entity_id=insurance.id,
            details={"desconto_percentual": str(insurance.discount_percent)},
        )
        self.db.commit()
        return insurance

    def update(self, actor: User, insurance_id: int, data: InsuranceUpdate) -> HealthInsurance:
        insurance = self.get(insurance_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            raise BusinessRuleError("Nenhum campo informado para atualização.")
        if "name" in changes and self.repo.name_exists(changes["name"], exclude_id=insurance.id):
            raise ConflictError("Já existe um convênio com este nome.")
        if changes.get("ans_code") and self.repo.ans_code_exists(changes["ans_code"], exclude_id=insurance.id):
            raise ConflictError("Já existe um convênio com este registro ANS.")
        for field, value in changes.items():
            setattr(insurance, field, value)
        self.audit.log(
            AuditAction.INSURANCE_UPDATED,
            actor=actor,
            entity_type="convenio",
            entity_id=insurance.id,
            details={"campos": sorted(changes)},
        )
        self.db.commit()
        return insurance
