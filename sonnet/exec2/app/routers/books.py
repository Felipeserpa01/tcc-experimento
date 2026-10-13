from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_librarian
from app.models import Book
from app.schemas import BookCreate, BookOut, BookUpdate

router = APIRouter(prefix="/books", tags=["books"])


@router.post("/", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(
    book_in: BookCreate,
    db: Session = Depends(get_db),
    _librarian=Depends(require_librarian),
):
    book = Book(
        title=book_in.title,
        author=book_in.author,
        isbn=book_in.isbn,
        year=book_in.year,
        total_copies=book_in.total_copies,
        available_copies=book_in.total_copies,
    )
    db.add(book)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ISBN already registered")
    db.refresh(book)
    return book


@router.get("/", response_model=list[BookOut])
def list_books(
    q: str | None = Query(default=None, description="Search by title or author"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(Book)
    if q:
        pattern = f"%{q}%"
        query = query.filter(or_(Book.title.ilike(pattern), Book.author.ilike(pattern)))
    return query.order_by(Book.id).offset(skip).limit(limit).all()


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


@router.put("/{book_id}", response_model=BookOut)
def update_book(
    book_id: int,
    book_in: BookUpdate,
    db: Session = Depends(get_db),
    _librarian=Depends(require_librarian),
):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    update_data = book_in.model_dump(exclude_unset=True)
    if "total_copies" in update_data:
        new_total = update_data["total_copies"]
        on_loan = book.total_copies - book.available_copies
        if new_total < on_loan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot set total_copies below the {on_loan} copies currently on loan",
            )
        book.available_copies = new_total - on_loan

    for field, value in update_data.items():
        setattr(book, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ISBN already registered")
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    _librarian=Depends(require_librarian),
):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if book.available_copies < book.total_copies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a book that currently has active loans",
        )
    db.delete(book)
    db.commit()
    return None
