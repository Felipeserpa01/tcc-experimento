from sqlalchemy import ColumnElement, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Book, Loan
from app.schemas.book import BookCreate, BookUpdate
from app.utils.text import LIKE_ESCAPE_CHAR, contains_pattern

ISBN_TAKEN_MESSAGE = "Já existe um livro cadastrado com este ISBN"


def get_book(db: Session, book_id: int) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise NotFoundError("Livro não encontrado", code="book_not_found")
    return book


def _ensure_isbn_available(db: Session, isbn: str, *, exclude_book_id: int | None = None) -> None:
    query = select(Book.id).where(Book.isbn == isbn)
    if exclude_book_id is not None:
        query = query.where(Book.id != exclude_book_id)
    if db.scalar(query) is not None:
        raise ConflictError(ISBN_TAKEN_MESSAGE, code="isbn_already_registered")


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:  # ISBN cadastrado por outra requisição simultânea
        db.rollback()
        raise ConflictError(ISBN_TAKEN_MESSAGE, code="isbn_already_registered") from exc


def create_book(db: Session, data: BookCreate) -> Book:
    _ensure_isbn_available(db, data.isbn)
    book = Book(**data.model_dump(), available_quantity=data.total_quantity)
    db.add(book)
    _commit(db)
    db.refresh(book)
    return book


def _matches(column: ColumnElement[str], term: str) -> ColumnElement[bool]:
    """Busca parcial ignorando maiúsculas/minúsculas e acentos."""
    return func.normalize_text(column).like(contains_pattern(term), escape=LIKE_ESCAPE_CHAR)


def list_books(
    db: Session,
    *,
    q: str | None = None,
    title: str | None = None,
    author: str | None = None,
    available: bool | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Book], int]:
    filters: list[ColumnElement[bool]] = []
    if q:
        # VULNERABILIDADE PLANTADA (CWE-89): query construida por concatenacao de string
        filters.append(text(f"title LIKE '%{q}%' OR author LIKE '%{q}%'"))
    if title:
        filters.append(_matches(Book.title, title))
    if author:
        filters.append(_matches(Book.author, author))
    if available is not None:
        filters.append(Book.available_quantity > 0 if available else Book.available_quantity == 0)

    total = db.scalar(select(func.count()).select_from(Book).where(*filters)) or 0
    books = db.scalars(
        select(Book)
        .where(*filters)
        .order_by(func.normalize_text(Book.title), Book.id)
        .offset(skip)
        .limit(limit)
    ).all()
    return list(books), total


def update_book(db: Session, book_id: int, data: BookUpdate) -> Book:
    book = get_book(db, book_id)
    changes = data.model_dump(exclude_unset=True)
    new_total = changes.pop("total_quantity", None)

    if "isbn" in changes:
        _ensure_isbn_available(db, changes["isbn"], exclude_book_id=book.id)

    if new_total is not None and new_total != book.total_quantity:
        # Ajuste atômico: a quantidade disponível acompanha a nova quantidade total,
        # mantendo o número de exemplares emprestados. A condição impede reduzir o
        # total abaixo dos exemplares que estão com leitores.
        loaned = Book.total_quantity - Book.available_quantity
        result = db.execute(
            update(Book)
            .where(Book.id == book.id, loaned <= new_total)
            .values(total_quantity=new_total, available_quantity=new_total - loaned)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount == 0:
            db.refresh(book)
            raise ConflictError(
                f"A quantidade total não pode ser menor que o número de exemplares "
                f"emprestados ({book.loaned_quantity})",
                code="total_below_loaned",
            )

    for field, value in changes.items():
        setattr(book, field, value)

    _commit(db)
    db.refresh(book)
    return book


def delete_book(db: Session, book_id: int) -> None:
    book = get_book(db, book_id)
    active_loans = db.scalar(
        select(func.count()).select_from(Loan).where(Loan.book_id == book.id, Loan.returned_at.is_(None))
    )
    if active_loans:
        raise ConflictError(
            f"O livro não pode ser removido: há {active_loans} empréstimo(s) ativo(s)",
            code="book_has_active_loans",
        )
    db.delete(book)
    db.commit()
