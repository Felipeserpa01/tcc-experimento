from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models.book import Book
from app.models.user import User, UserType
from app.schemas.book import BookCreate, BookResponse, BookUpdate, BookSearch
from app.security.jwt import get_current_user
from app.utils.validators import is_valid_isbn

router = APIRouter(prefix="/books", tags=["books"])

def get_librarian_user(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user or user.user_type != UserType.LIBRARIAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only librarians can perform this action"
        )
    return current_user

@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    book: BookCreate,
    current_user: dict = Depends(get_librarian_user),
    db: Session = Depends(get_db)
):
    if not is_valid_isbn(book.isbn):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ISBN format"
        )

    existing_book = db.query(Book).filter(Book.isbn == book.isbn).first()
    if existing_book:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A book with this ISBN already exists"
        )

    db_book = Book(
        title=book.title,
        author=book.author,
        isbn=book.isbn,
        year=book.year,
        total_quantity=book.total_quantity,
        available_quantity=book.total_quantity,
        description=book.description
    )

    db.add(db_book)
    db.commit()
    db.refresh(db_book)

    return db_book

@router.get("/", response_model=list[BookResponse])
async def list_books(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    books = db.query(Book).offset(skip).limit(limit).all()
    return books

@router.get("/search", response_model=list[BookResponse])
async def search_books(
    title: str | None = None,
    author: str | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Book)

    if title:
        query = query.filter(Book.title.ilike(f"%{title}%"))

    if author:
        query = query.filter(Book.author.ilike(f"%{author}%"))

    if not title and not author:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one search parameter (title or author)"
        )

    return query.all()

@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    return book

@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    book_update: BookUpdate,
    current_user: dict = Depends(get_librarian_user),
    db: Session = Depends(get_db)
):
    db_book = db.query(Book).filter(Book.id == book_id).first()

    if not db_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    update_data = book_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_book, field, value)

    db.add(db_book)
    db.commit()
    db.refresh(db_book)

    return db_book

@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: int,
    current_user: dict = Depends(get_librarian_user),
    db: Session = Depends(get_db)
):
    db_book = db.query(Book).filter(Book.id == book_id).first()

    if not db_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    db.delete(db_book)
    db.commit()

    return None
