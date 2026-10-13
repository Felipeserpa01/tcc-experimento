from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import CurrentUser, DbSession, PaginationParams, require_librarian
from app.models import Book
from app.schemas.book import BookCreate, BookRead, BookUpdate
from app.schemas.common import ErrorResponse, Page
from app.services import book_service

router = APIRouter(prefix="/books", tags=["Livros"])

BookId = Annotated[int, Path(gt=0)]
SearchTerm = Annotated[str | None, Query(max_length=255)]


def _clean(term: str | None) -> str | None:
    if term is None:
        return None
    return term.strip() or None


@router.post(
    "",
    response_model=BookRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar livro",
    dependencies=[Depends(require_librarian)],
    responses={409: {"model": ErrorResponse, "description": "ISBN já cadastrado"}},
)
def create_book(data: BookCreate, db: DbSession) -> Book:
    return book_service.create_book(db, data)


@router.get("", response_model=Page[BookRead], summary="Listar e buscar livros")
def list_books(
    _: CurrentUser,
    db: DbSession,
    pagination: PaginationParams,
    q: Annotated[SearchTerm, Query(description="Busca no título ou no autor.")] = None,
    title: Annotated[SearchTerm, Query(description="Busca parcial pelo título.")] = None,
    author: Annotated[SearchTerm, Query(description="Busca parcial pelo autor.")] = None,
    available: Annotated[
        bool | None, Query(description="true: com exemplares disponíveis; false: sem exemplares.")
    ] = None,
) -> Page[BookRead]:
    """Buscas ignoram maiúsculas/minúsculas e acentos."""
    books, total = book_service.list_books(
        db,
        q=_clean(q),
        title=_clean(title),
        author=_clean(author),
        available=available,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return Page[BookRead](
        items=[BookRead.model_validate(book) for book in books],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get(
    "/{book_id}",
    response_model=BookRead,
    summary="Consultar livro",
    responses={404: {"model": ErrorResponse}},
)
def read_book(book_id: BookId, _: CurrentUser, db: DbSession) -> Book:
    return book_service.get_book(db, book_id)


@router.patch(
    "/{book_id}",
    response_model=BookRead,
    summary="Atualizar livro",
    dependencies=[Depends(require_librarian)],
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse, "description": "ISBN duplicado ou total menor que o emprestado"},
    },
)
def update_book(book_id: BookId, data: BookUpdate, db: DbSession) -> Book:
    return book_service.update_book(db, book_id, data)


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover livro",
    dependencies=[Depends(require_librarian)],
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse, "description": "Livro com empréstimos ativos"},
    },
)
def delete_book(book_id: BookId, db: DbSession) -> None:
    book_service.delete_book(db, book_id)
