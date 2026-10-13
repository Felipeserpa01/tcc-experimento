from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from app.core.pagination import PageParams, PaginatedResponse
from typing import TypeVar, Generic, Type, List, Optional

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, db: Session, model: Type[T]):
        self.db = db
        self.model = model

    def get(self, id: int) -> Optional[T]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def list(self, filters: dict = None, pagination: PageParams = None) -> PaginatedResponse[T]:
        query = self.db.query(self.model)

        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)

        total = query.count()

        if pagination:
            if hasattr(self.model, pagination.sort_by):
                sort_column = getattr(self.model, pagination.sort_by)
                if pagination.order.lower() == "desc":
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(asc(sort_column))

            items = query.offset(pagination.get_offset()).limit(pagination.get_limit()).all()
        else:
            items = query.all()

        pages = (total + pagination.size - 1) // pagination.size if pagination else 1

        return PaginatedResponse(
            total=total,
            page=pagination.page if pagination else 1,
            size=pagination.size if pagination else len(items),
            pages=pages,
            items=items
        )

    def create(self, obj: dict) -> T:
        db_obj = self.model(**obj)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, id: int, obj: dict) -> Optional[T]:
        db_obj = self.get(id)
        if db_obj:
            for key, value in obj.items():
                if hasattr(db_obj, key):
                    setattr(db_obj, key, value)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: int) -> bool:
        db_obj = self.get(id)
        if db_obj:
            self.db.delete(db_obj)
            self.db.commit()
            return True
        return False
