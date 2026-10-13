from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_librarian, get_current_user
from app.models import Book, Loan
from app.schemas import BookCreate, BookOut, BookUpdate

router = APIRouter(prefix="/books", tags=["Books"])


@router.post("/", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(
    book_in: BookCreate,
    db: Session = Depends(get_db),
    _librarian=Depends(get_current_librarian),
):
    if db.query(Book).filter(Book.isbn == book_in.isbn).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A book with this ISBN already exists")

    book = Book(
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


@router.get("/", response_model=list[BookOut])
def list_books(
    title: str | None = Query(default=None, description="Filter by (partial) title"),
    author: str | None = Query(default=None, description="Filter by (partial) author"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    query = db.query(Book)
    if title:
        query = query.filter(Book.title.ilike(f"%{title}%"))
    if author:
        query = query.filter(Book.author.ilike(f"%{author}%"))
    return query.order_by(Book.id).offset(skip).limit(limit).all()


@router.get("/{book_id}", response_model=BookOut)
def get_book(
    book_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


@router.put("/{book_id}", response_model=BookOut)
def update_book(
    book_id: int,
    book_in: BookUpdate,
    db: Session = Depends(get_db),
    _librarian=Depends(get_current_librarian),
):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    if book_in.isbn and book_in.isbn != book.isbn:
        if db.query(Book).filter(Book.isbn == book_in.isbn, Book.id != book_id).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A book with this ISBN already exists")
        book.isbn = book_in.isbn

    if book_in.title is not None:
        book.title = book_in.title
    if book_in.author is not None:
        book.author = book_in.author
    if book_in.year is not None:
        book.year = book_in.year

    if book_in.total_quantity is not None:
        currently_loaned = book.total_quantity - book.available_quantity
        if book_in.total_quantity < currently_loaned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Cannot set total_quantity below the number of copies currently loaned "
                    f"({currently_loaned})"
                ),
            )
        book.total_quantity = book_in.total_quantity
        book.available_quantity = book_in.total_quantity - currently_loaned

    db.commit()
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    _librarian=Depends(get_current_librarian),
):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    has_active_loans = (
        db.query(Loan).filter(Loan.book_id == book_id, Loan.return_date.is_(None)).first()
    )
    if has_active_loans:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a book with active loans",
        )

    db.delete(book)
    db.commit()
    return None
