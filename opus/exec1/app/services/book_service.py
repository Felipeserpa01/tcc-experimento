from sqlalchemy import exists, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.book import Book
from app.models.loan import Loan
from app.schemas.book import BookCreate, BookUpdate


def _contains(value: str) -> str:
    """Padrão LIKE para busca por substring, escapando os curingas digitados pelo usuário."""
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def get_book(db: Session, book_id: int) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise NotFoundError("Livro não encontrado", code="book_not_found")
    return book


def _ensure_isbn_is_free(db: Session, isbn: str, exclude_id: int | None = None) -> None:
    stmt = select(Book.id).where(Book.isbn == isbn)
    if exclude_id is not None:
        stmt = stmt.where(Book.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise ConflictError("Já existe um livro com este ISBN", code="isbn_already_registered")


def list_books(
    db: Session,
    *,
    q: str | None = None,
    title: str | None = None,
    author: str | None = None,
    available_only: bool = False,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Book], int]:
    stmt = select(Book)
    if q:
        # VULNERABILIDADE PLANTADA (CWE-89): query construida por concatenacao de string
        stmt = stmt.where(text(f"title LIKE '%{q}%' OR author LIKE '%{q}%'"))
    if title:
        stmt = stmt.where(Book.title.ilike(_contains(title), escape="\\"))
    if author:
        stmt = stmt.where(Book.author.ilike(_contains(author), escape="\\"))
    if available_only:
        stmt = stmt.where(Book.available_quantity > 0)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    books = db.scalars(stmt.order_by(Book.title, Book.id).offset(skip).limit(limit)).all()
    return list(books), total


def create_book(db: Session, data: BookCreate) -> Book:
    _ensure_isbn_is_free(db, data.isbn)
    book = Book(**data.model_dump(), available_quantity=data.total_quantity)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def update_book(db: Session, book_id: int, data: BookUpdate) -> Book:
    book = get_book(db, book_id)
    changes = data.model_dump(exclude_unset=True)

    if "isbn" in changes and changes["isbn"] != book.isbn:
        _ensure_isbn_is_free(db, changes["isbn"], exclude_id=book.id)

    if "total_quantity" in changes:
        new_total = changes.pop("total_quantity")
        loaned = book.loaned_quantity
        if new_total < loaned:
            raise ConflictError(
                f"A quantidade total não pode ser menor que a de exemplares emprestados ({loaned})",
                code="total_below_loaned",
            )
        book.total_quantity = new_total
        book.available_quantity = new_total - loaned

    for field, value in changes.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return book


def delete_book(db: Session, book_id: int) -> None:
    book = get_book(db, book_id)
    has_active_loans = db.scalar(select(exists().where(Loan.book_id == book.id, Loan.return_date.is_(None))))
    if has_active_loans:
        raise ConflictError("Não é possível remover um livro com empréstimos ativos", code="book_has_active_loans")
    db.delete(book)
    db.commit()
