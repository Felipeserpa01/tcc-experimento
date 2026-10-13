from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_user, require_librarian

router = APIRouter(prefix="/books", tags=["Livros"])


@router.post("/", response_model=schemas.BookOut, status_code=status.HTTP_201_CREATED)
def create_book(
    book_in: schemas.BookCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_librarian),
):
    if db.query(models.Book).filter(models.Book.isbn == book_in.isbn).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ISBN já cadastrado")

    book = models.Book(
        title=book_in.title,
        author=book_in.author,
        isbn=book_in.isbn,
        year=book_in.year,
        total_quantity=book_in.total_quantity,
        available_quantity=book_in.total_quantity,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.get("/", response_model=List[schemas.BookOut])
def list_books(
    search: Optional[str] = Query(None, description="Busca por título ou autor"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    query = db.query(models.Book)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(models.Book.title.ilike(like), models.Book.author.ilike(like)))
    return query.order_by(models.Book.id).offset(skip).limit(limit).all()


@router.get("/{book_id}", response_model=schemas.BookOut)
def get_book(
    book_id: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)
):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Livro não encontrado")
    return book


@router.put("/{book_id}", response_model=schemas.BookOut)
def update_book(
    book_id: int,
    book_in: schemas.BookUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_librarian),
):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Livro não encontrado")

    update_data = book_in.model_dump(exclude_unset=True)

    if "isbn" in update_data and update_data["isbn"] != book.isbn:
        existing = db.query(models.Book).filter(models.Book.isbn == update_data["isbn"]).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="ISBN já cadastrado"
            )

    if "total_quantity" in update_data:
        delta = update_data["total_quantity"] - book.total_quantity
        new_available = book.available_quantity + delta
        if new_available < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Não é possível reduzir a quantidade total abaixo do número de "
                    "exemplares atualmente emprestados"
                ),
            )
        book.available_quantity = new_available

    for field, value in update_data.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_librarian),
):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Livro não encontrado")

    active_loans = (
        db.query(models.Loan)
        .filter(models.Loan.book_id == book_id, models.Loan.return_date.is_(None))
        .count()
    )
    if active_loans > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível remover um livro com empréstimos ativos",
        )

    db.delete(book)
    db.commit()
    return None
