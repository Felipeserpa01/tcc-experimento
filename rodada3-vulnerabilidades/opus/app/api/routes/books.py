from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, DbSession, Librarian, PageParams
from app.schemas.book import BookCreate, BookRead, BookUpdate
from app.schemas.common import ErrorResponse, Page
from app.services import book_service

router = APIRouter(prefix="/books", tags=["Livros"])

NOT_FOUND = {404: {"model": ErrorResponse}}


@router.post(
    "",
    response_model=BookRead,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
)
def create_book(data: BookCreate, db: DbSession, _: Librarian) -> BookRead:
    """Cadastra um livro. A quantidade disponível começa igual à quantidade total."""
    return book_service.create_book(db, data)


@router.get("", response_model=Page[BookRead])
def list_books(
    db: DbSession,
    _: CurrentUser,
    page: PageParams,
    q: Annotated[str | None, Query(max_length=255, description="Busca no título ou no autor")] = None,
    title: Annotated[str | None, Query(max_length=255, description="Filtra por parte do título")] = None,
    author: Annotated[str | None, Query(max_length=255, description="Filtra por parte do autor")] = None,
    available_only: Annotated[bool, Query(description="Somente livros com exemplares disponíveis")] = False,
) -> Page[BookRead]:
    """Lista livros com busca (sem diferenciar maiúsculas/minúsculas) por título e/ou autor."""
    books, total = book_service.list_books(
        db, q=q, title=title, author=author, available_only=available_only, skip=page.skip, limit=page.limit
    )
    return Page(items=books, total=total, skip=page.skip, limit=page.limit)


@router.get("/{book_id}", response_model=BookRead, responses=NOT_FOUND)
def read_book(book_id: int, db: DbSession, _: CurrentUser) -> BookRead:
    return book_service.get_book(db, book_id)


@router.patch(
    "/{book_id}",
    response_model=BookRead,
    responses={**NOT_FOUND, 409: {"model": ErrorResponse}},
)
def update_book(book_id: int, data: BookUpdate, db: DbSession, _: Librarian) -> BookRead:
    """Atualiza parcialmente um livro.

    Ao alterar `total_quantity`, a quantidade disponível é ajustada mantendo os exemplares
    emprestados; o novo total não pode ser menor que a quantidade emprestada.
    """
    return book_service.update_book(db, book_id, data)


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**NOT_FOUND, 409: {"model": ErrorResponse}},
)
def delete_book(book_id: int, db: DbSession, _: Librarian) -> Response:
    """Remove um livro e seu histórico de empréstimos. Livros com empréstimos ativos não podem ser removidos."""
    book_service.delete_book(db, book_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
