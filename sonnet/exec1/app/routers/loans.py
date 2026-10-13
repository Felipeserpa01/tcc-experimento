from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_librarian, get_current_user
from app.models import Book, Loan, User, UserRole
from app.schemas import LoanCreate, LoanOut

router = APIRouter(prefix="/loans", tags=["Loans"])


@router.post("/", response_model=LoanOut, status_code=status.HTTP_201_CREATED)
def create_loan(
    loan_in: LoanCreate,
    db: Session = Depends(get_db),
    _librarian: User = Depends(get_current_librarian),
):
    reader = db.get(User, loan_in.reader_id)
    if not reader:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reader not found")
    if reader.role != UserRole.LEITOR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loans can only be registered for users with role 'leitor'",
        )

    book = db.get(Book, loan_in.book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    if book.available_quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No available copies of this book",
        )

    active_loans_count = (
        db.query(Loan)
        .filter(Loan.reader_id == reader.id, Loan.return_date.is_(None))
        .count()
    )
    if active_loans_count >= settings.MAX_ACTIVE_LOANS_PER_READER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Reader already has {active_loans_count} active loans "
                f"(limit is {settings.MAX_ACTIVE_LOANS_PER_READER})"
            ),
        )

    today = date.today()
    loan = Loan(
        book_id=book.id,
        reader_id=reader.id,
        loan_date=today,
        due_date=today + timedelta(days=settings.LOAN_PERIOD_DAYS),
    )
    book.available_quantity -= 1

    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


@router.post("/{loan_id}/return", response_model=LoanOut)
def return_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    _librarian: User = Depends(get_current_librarian),
):
    loan = db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    if loan.return_date is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This loan was already returned")

    today = date.today()
    loan.return_date = today

    days_late = (today - loan.due_date).days
    loan.fine_amount = round(days_late * settings.FINE_PER_DAY, 2) if days_late > 0 else 0.0

    book = db.get(Book, loan.book_id)
    if book:
        book.available_quantity = min(book.total_quantity, book.available_quantity + 1)

    db.commit()
    db.refresh(loan)
    return loan


@router.get("/me", response_model=list[LoanOut])
def list_my_loans(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Loan).filter(Loan.reader_id == current_user.id)
    if active_only:
        query = query.filter(Loan.return_date.is_(None))
    return query.order_by(Loan.id).all()


@router.get("/reader/{reader_id}", response_model=list[LoanOut])
def list_reader_loans(
    reader_id: int,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.BIBLIOTECARIO and current_user.id != reader_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own loans",
        )

    reader = db.get(User, reader_id)
    if not reader:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reader not found")

    query = db.query(Loan).filter(Loan.reader_id == reader_id)
    if active_only:
        query = query.filter(Loan.return_date.is_(None))
    return query.order_by(Loan.id).all()


@router.get("/", response_model=list[LoanOut])
def list_all_loans(
    active_only: bool = False,
    db: Session = Depends(get_db),
    _librarian: User = Depends(get_current_librarian),
):
    query = db.query(Loan)
    if active_only:
        query = query.filter(Loan.return_date.is_(None))
    return query.order_by(Loan.id).all()
