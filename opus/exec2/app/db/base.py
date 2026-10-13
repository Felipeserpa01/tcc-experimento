from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """Armazena datetimes em UTC e os devolve sempre com fuso horário (UTC).

    O SQLite não guarda fuso horário; sem este tipo, a aplicação receberia
    datetimes "naive" e comparações com datas "aware" falhariam.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Datetimes sem fuso horário não são aceitos")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


class Base(DeclarativeBase):
    pass
