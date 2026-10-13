from sqlalchemy.orm import Session
from app.models.patient import Patient
from .base_repository import BaseRepository


class PatientRepository(BaseRepository[Patient]):
    def __init__(self, db: Session):
        super().__init__(db, Patient)

    def get_by_cpf(self, cpf: str) -> Patient | None:
        return self.db.query(Patient).filter(Patient.cpf == cpf).first()

    def get_by_user_id(self, user_id: int) -> Patient | None:
        return self.db.query(Patient).filter(Patient.user_id == user_id).first()

    def search_by_name(self, name: str, pagination=None):
        query = self.db.query(Patient).filter(Patient.full_name.ilike(f"%{name}%"))
        total = query.count()

        if pagination:
            items = query.offset(pagination.get_offset()).limit(pagination.get_limit()).all()
        else:
            items = query.all()

        from app.core.pagination import PaginatedResponse
        return PaginatedResponse(
            total=total,
            page=pagination.page if pagination else 1,
            size=pagination.size if pagination else len(items),
            pages=(total + pagination.size - 1) // pagination.size if pagination else 1,
            items=items
        )
