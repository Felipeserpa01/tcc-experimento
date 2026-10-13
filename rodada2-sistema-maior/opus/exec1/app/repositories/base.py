"""Repositorio generico: isola o acesso ao banco da camada de servico."""

from __future__ import annotations

from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    model: type[ModelType]

    def __init__(self, db: Session) -> None:
        self.db = db

    # -- Leitura -----------------------------------------------------------
    def get(self, obj_id: int) -> ModelType | None:
        return self.db.get(self.model, obj_id)

    def get_by(self, **filters: Any) -> ModelType | None:
        stmt = select(self.model).filter_by(**filters).limit(1)
        return self.db.execute(stmt).scalars().first()

    def exists(self, **filters: Any) -> bool:
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        return (self.db.execute(stmt).scalar_one() or 0) > 0

    def list_all(self, **filters: Any) -> list[ModelType]:
        stmt = select(self.model).filter_by(**filters)
        return list(self.db.execute(stmt).scalars().all())

    def count(self, **filters: Any) -> int:
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        return self.db.execute(stmt).scalar_one() or 0

    # -- Escrita -----------------------------------------------------------
    def add(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        self.db.flush()
        return obj

    def create(self, **data: Any) -> ModelType:
        obj = self.model(**data)
        return self.add(obj)

    def update(self, obj: ModelType, data: dict[str, Any]) -> ModelType:
        for field, value in data.items():
            setattr(obj, field, value)
        self.db.flush()
        return obj

    def delete(self, obj: ModelType) -> None:
        self.db.delete(obj)
        self.db.flush()

    # -- Paginacao ---------------------------------------------------------
    def paginate(self, stmt: Select, page: int, size: int) -> tuple[list[ModelType], int]:
        total = self.count_statement(stmt)
        offset = (page - 1) * size
        rows = self.db.execute(stmt.offset(offset).limit(size)).scalars().unique().all()
        return list(rows), total

    def count_statement(self, stmt: Select) -> int:
        count_stmt = select(func.count()).select_from(
            stmt.order_by(None).subquery()
        )
        return self.db.execute(count_stmt).scalar_one() or 0

    @staticmethod
    def apply_order(stmt: Select, column: Any, descending: bool) -> Select:
        return stmt.order_by(column.desc() if descending else column.asc())

    @staticmethod
    def rows_to_list(rows: Sequence[Any]) -> list[Any]:
        return list(rows)
