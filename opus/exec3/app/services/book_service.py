from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.book import Book
from app.models.loan import Loan
from app.schemas.book import BookCreate, BookUpdate


def get_book(db: Session, book_id: int) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise NotFoundError("Livro não encontrado.")
    return book


def list_books(
    db: Session,
    *,
    title: str | None = None,
    author: str | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Book]:
    stmt = select(Book)
    # autoescape: '%' e '_' digitados pelo usuário são tratados como texto literal.
    if title:
        stmt = stmt.where(Book.title.icontains(title, autoescape=True))
    if author:
        stmt = stmt.where(Book.author.icontains(author, autoescape=True))
    if q:
        stmt = stmt.where(
            or_(Book.title.icontains(q, autoescape=True), Book.author.icontains(q, autoescape=True))
        )
    stmt = stmt.order_by(Book.title, Book.id).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def count_active_loans(db: Session, book_id: int) -> int:
    stmt = select(func.count()).select_from(Loan).where(Loan.book_id == book_id, Loan.return_date.is_(None))
    return db.scalar(stmt) or 0


def _ensure_isbn_is_free(db: Session, isbn: str) -> None:
    if db.scalar(select(Book.id).where(Book.isbn == isbn)) is not None:
        raise ConflictError("Já existe um livro cadastrado com este ISBN.")


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
        _ensure_isbn_is_free(db, changes["isbn"])

    if "total_quantity" in changes:
        on_loan = count_active_loans(db, book.id)
        if changes["total_quantity"] < on_loan:
            raise ConflictError(
                f"A quantidade total não pode ser menor que o número de exemplares emprestados ({on_loan})."
            )
        book.available_quantity = changes["total_quantity"] - on_loan

    for field, value in changes.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return book


def delete_book(db: Session, book_id: int) -> None:
    book = get_book(db, book_id)
    if count_active_loans(db, book.id) > 0:
        raise ConflictError("Não é possível remover um livro que possui empréstimos ativos.")
    db.delete(book)
    db.commit()
