from fastapi import Query
from pydantic import BaseModel

from app.config import get_settings

settings = get_settings()


class PageParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Número da página"),
        page_size: int = Query(
            settings.default_page_size, ge=1, le=settings.max_page_size, description="Itens por página"
        ),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size


class PagedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list
