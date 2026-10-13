from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models import Loan, Book
from app.schemas.loan import LoanCreate


def create_loan(db: Session, reader_id: int, loan: LoanCreate):
    book = db.query(Book).filter(Book.id == loan.book_id).first()
    if not book:
        return None

    if book.available_quantity <= 0:
        return False

    due_date = datetime.utcnow() + timedelta(days=14)
    db_loan = Loan(
        book_id=loan.book_id,
        reader_id=reader_id,
        due_date=due_date,
    )

    book.available_quantity -= 1
    db.add(db_loan)
    db.commit()
    db.refresh(db_loan)
    return db_loan


def get_active_loans(db: Session, reader_id: int):
    return db.query(Loan).filter(
        Loan.reader_id == reader_id,
        Loan.return_date.is_(None)
    ).all()


def get_loans_count(db: Session, reader_id: int):
    return db.query(Loan).filter(
        Loan.reader_id == reader_id,
        Loan.return_date.is_(None)
    ).count()


def get_loan_by_id(db: Session, loan_id: int):
    return db.query(Loan).filter(Loan.id == loan_id).first()


def return_loan(db: Session, loan_id: int, return_date: datetime):
    db_loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not db_loan or db_loan.return_date:
        return None

    db_loan.return_date = return_date

    if return_date > db_loan.due_date:
        days_late = (return_date - db_loan.due_date).days
        daily_fine = 5.0
        db_loan.fine = days_late * daily_fine

    book = db.query(Book).filter(Book.id == db_loan.book_id).first()
    if book:
        book.available_quantity += 1

    db.commit()
    db.refresh(db_loan)
    return db_loan
