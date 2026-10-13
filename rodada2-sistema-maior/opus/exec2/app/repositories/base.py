"""Repositório base: operações genéricas de persistência e paginação."""

from collections.abc import Mapping
from typing import Any, ClassVar, Generic, TypeVar

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.pagination import PageParams, PageResult, SortParams

ModelT = TypeVar("ModelT", bound=Base)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def contains_ci(column: Any, value: str) -> ColumnElement[bool]:
    """``column`` contém ``value`` (sem diferenciar maiúsculas), com curingas escapados."""
    return func.lower(column).like(f"%{_escape_like(value.lower())}%", escape="\\")


def starts_with(column: Any, value: str) -> ColumnElement[bool]:
    return column.like(f"{_escape_like(value)}%", escape="\\")


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]
    #: Campos aceitos em ``sort_by`` mapeados para colunas (whitelist contra injeção).
    sortable_columns: ClassVar[Mapping[str, Any]] = {}

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, entity_id: int) -> ModelT | None:
        return self.db.get(self.model, entity_id)

    def add(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        self.db.flush()
        return entity

    def add_all(self, entities: list[ModelT]) -> list[ModelT]:
        self.db.add_all(entities)
        self.db.flush()
        return entities

    def delete(self, entity: ModelT) -> None:
        self.db.delete(entity)
        self.db.flush()

    def paginate(self, stmt: Select, page: PageParams, sort: SortParams | None = None) -> PageResult[ModelT]:
        total = self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        if sort is not None:
            column = self.sortable_columns[sort.field]
            primary = column.desc() if sort.descending else column.asc()
            tie_breaker = self.model.id.desc() if sort.descending else self.model.id.asc()  # type: ignore[attr-defined]
            stmt = stmt.order_by(None).order_by(primary, tie_breaker)
        items = list(self.db.scalars(stmt.offset(page.offset).limit(page.page_size)).unique().all())
        return PageResult(items, total, page)
