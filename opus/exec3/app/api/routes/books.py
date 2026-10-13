from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, DbSession, Librarian
from app.models.book import Book
from app.schemas.book import BookCreate, BookOut, BookUpdate
from app.services import book_service

router = APIRouter(prefix="/books", tags=["Livros"])


@router.post(
    "",
    response_model=BookOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar livro (bibliotecário)",
    responses={409: {"description": "ISBN já cadastrado"}},
)
def create_book(data: BookCreate, _: Librarian, db: DbSession) -> Book:
    """A quantidade disponível começa igual à quantidade total."""
    return book_service.create_book(db, data)


@router.get("", response_model=list[BookOut], summary="Listar e buscar livros")
def list_books(
    _: CurrentUser,
    db: DbSession,
    title: str | None = Query(None, min_length=1, max_length=255, description="Parte do título"),
    author: str | None = Query(None, min_length=1, max_length=255, description="Parte do nome do autor"),
    q: str | None = Query(None, min_length=1, max_length=255, description="Busca no título OU no autor"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[Book]:
    """A busca não diferencia maiúsculas de minúsculas e aceita trechos parciais."""
    return book_service.list_books(db, title=title, author=author, q=q, skip=skip, limit=limit)


@router.get("/{book_id}", response_model=BookOut, summary="Consultar livro")
def read_book(book_id: int, _: CurrentUser, db: DbSession) -> Book:
    return book_service.get_book(db, book_id)


@router.patch(
    "/{book_id}",
    response_model=BookOut,
    summary="Atualizar livro (bibliotecário)",
    responses={409: {"description": "ISBN duplicado ou total menor que exemplares emprestados"}},
)
def update_book(book_id: int, data: BookUpdate, _: Librarian, db: DbSession) -> Book:
    """Atualização parcial. Ao alterar `total_quantity`, a quantidade disponível é recalculada."""
    return book_service.update_book(db, book_id, data)


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover livro (bibliotecário)",
    responses={409: {"description": "Livro com empréstimos ativos"}},
)
def delete_book(book_id: int, _: Librarian, db: DbSession) -> Response:
    book_service.delete_book(db, book_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
