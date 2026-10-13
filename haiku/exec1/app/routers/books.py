from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Book, User
from app.schemas import BookCreate, BookUpdate, BookResponse, SearchBooksResponse
from app.dependencies import get_current_user, get_current_librarian

router = APIRouter(prefix="/api/books", tags=["books"])


@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    book_data: BookCreate,
    current_user: User = Depends(get_current_librarian),
    db: Session = Depends(get_db),
):
    existing_book = db.query(Book).filter(Book.isbn == book_data.isbn).first()
    if existing_book:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Livro com este ISBN já existe",
        )

    db_book = Book(
        title=book_data.title,
        author=book_data.author,
        isbn=book_data.isbn,
        year=book_data.year,
        total_quantity=book_data.total_quantity,
        available_quantity=book_data.total_quantity,
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


@router.get("/", response_model=list[BookResponse])
async def list_books(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    books = db.query(Book).offset(skip).limit(limit).all()
    return books


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro não encontrado",
        )
    return book


@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    book_data: BookUpdate,
    current_user: User = Depends(get_current_librarian),
    db: Session = Depends(get_db),
):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro não encontrado",
        )

    if book_data.title is not None:
        book.title = book_data.title
    if book_data.author is not None:
        book.author = book_data.author
    if book_data.year is not None:
        book.year = book_data.year
    if book_data.total_quantity is not None:
        quantity_diff = book_data.total_quantity - book.total_quantity
        book.total_quantity = book_data.total_quantity
        book.available_quantity += quantity_diff

    db.commit()
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: int,
    current_user: User = Depends(get_current_librarian),
    db: Session = Depends(get_db),
):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro não encontrado",
        )

    db.delete(book)
    db.commit()


@router.get("/search/by-title", response_model=SearchBooksResponse)
async def search_by_title(
    title: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    books = db.query(Book).filter(Book.title.ilike(f"%{title}%")).all()
    return {"books": books}


@router.get("/search/by-author", response_model=SearchBooksResponse)
async def search_by_author(
    author: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    books = db.query(Book).filter(Book.author.ilike(f"%{author}%")).all()
    return {"books": books}
