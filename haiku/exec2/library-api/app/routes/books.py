from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import verify_token
from app.schemas.book import BookCreate, BookUpdate, BookResponse
from app.crud.book import (
    create_book, get_books, get_book, update_book, delete_book, search_books
)

router = APIRouter(prefix="/books", tags=["books"])


def verify_librarian(token: dict = Depends(verify_token)):
    if token["role"] != "librarian":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only librarians can manage books"
        )
    return token


@router.post("/", response_model=BookResponse)
def create_new_book(
    book: BookCreate,
    token: dict = Depends(verify_librarian),
    db: Session = Depends(get_db)
):
    from app.models import Book
    db_book = db.query(Book).filter_by(isbn=book.isbn).first()
    if db_book:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ISBN already exists"
        )
    return create_book(db=db, book=book)


@router.get("/", response_model=list[BookResponse])
def list_books(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    return get_books(db, skip=skip, limit=limit)


@router.get("/search", response_model=list[BookResponse])
def search(
    q: str = Query(..., min_length=1),
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    return search_books(db, query=q)


@router.get("/{book_id}", response_model=BookResponse)
def get_book_detail(
    book_id: int,
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    return book


@router.put("/{book_id}", response_model=BookResponse)
def update_book_detail(
    book_id: int,
    book: BookUpdate,
    token: dict = Depends(verify_librarian),
    db: Session = Depends(get_db)
):
    db_book = update_book(db, book_id, book)
    if not db_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    return db_book


@router.delete("/{book_id}")
def delete_book_detail(
    book_id: int,
    token: dict = Depends(verify_librarian),
    db: Session = Depends(get_db)
):
    book = delete_book(db, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    return {"message": "Book deleted successfully"}
