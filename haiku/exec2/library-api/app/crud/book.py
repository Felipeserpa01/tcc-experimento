from sqlalchemy.orm import Session
from app.models import Book
from app.schemas.book import BookCreate, BookUpdate


def create_book(db: Session, book: BookCreate):
    db_book = Book(
        title=book.title,
        author=book.author,
        isbn=book.isbn,
        year=book.year,
        total_quantity=book.total_quantity,
        available_quantity=book.total_quantity,
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


def get_books(db: Session, skip: int = 0, limit: int = 10):
    return db.query(Book).offset(skip).limit(limit).all()


def get_book(db: Session, book_id: int):
    return db.query(Book).filter(Book.id == book_id).first()


def update_book(db: Session, book_id: int, book: BookUpdate):
    db_book = db.query(Book).filter(Book.id == book_id).first()
    if not db_book:
        return None

    update_data = book.model_dump(exclude_unset=True)
    if "total_quantity" in update_data:
        difference = update_data["total_quantity"] - db_book.total_quantity
        db_book.available_quantity = db_book.available_quantity + difference

    for field, value in update_data.items():
        if field != "total_quantity":
            setattr(db_book, field, value)

    if "total_quantity" in update_data:
        setattr(db_book, "total_quantity", update_data["total_quantity"])

    db.commit()
    db.refresh(db_book)
    return db_book


def delete_book(db: Session, book_id: int):
    db_book = db.query(Book).filter(Book.id == book_id).first()
    if db_book:
        db.delete(db_book)
        db.commit()
    return db_book


def search_books(db: Session, query: str):
    return db.query(Book).filter(
        (Book.title.ilike(f"%{query}%")) | (Book.author.ilike(f"%{query}%"))
    ).all()
