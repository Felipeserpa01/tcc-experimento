from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_librarian
from app.models import Book, Loan, User, UserRole
from app.schemas import LoanCreate, LoanOut, LoanReturnOut

router = APIRouter(prefix="/loans", tags=["loans"])


def _active_loans_query(db: Session, reader_id: int):
    return db.query(Loan).filter(Loan.reader_id == reader_id, Loan.return_date.is_(None))


@router.post("/", response_model=LoanOut, status_code=status.HTTP_201_CREATED)
def create_loan(
    loan_in: LoanCreate,
    db: Session = Depends(get_db),
    _librarian=Depends(require_librarian),
):
    reader = db.get(User, loan_in.reader_id)
    if reader is None or reader.role != UserRole.READER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reader not found")

    book = db.get(Book, loan_in.book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    if book.available_copies <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No available copies of this book",
        )

    active_count = _active_loans_query(db, reader.id).count()
    if active_count >= settings.max_loans_per_reader:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reader already has the maximum of {settings.max_loans_per_reader} active loans",
        )

    today = date.today()
    loan = Loan(
        book_id=book.id,
        reader_id=reader.id,
        loan_date=today,
        due_date=today + timedelta(days=settings.loan_period_days),
    )
    book.available_copies -= 1
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


@router.put("/{loan_id}/return", response_model=LoanReturnOut)
def return_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    _librarian=Depends(require_librarian),
):
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    if loan.return_date is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Loan already returned")

    loan.return_date = date.today()
    days_late = max(0, (loan.return_date - loan.due_date).days)
    loan.fine = round(days_late * settings.fine_per_day, 2)

    book = db.get(Book, loan.book_id)
    if book is not None:
        book.available_copies = min(book.total_copies, book.available_copies + 1)

    db.commit()
    db.refresh(loan)
    return LoanReturnOut(**LoanOut.model_validate(loan).model_dump(), days_late=days_late)


@router.get("/", response_model=list[LoanOut])
def list_loans(
    reader_id: int | None = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
    _librarian=Depends(require_librarian),
):
    query = db.query(Loan)
    if reader_id is not None:
        query = query.filter(Loan.reader_id == reader_id)
    if active_only:
        query = query.filter(Loan.return_date.is_(None))
    return query.order_by(Loan.id).all()


@router.get("/me", response_model=list[LoanOut])
def list_my_loans(
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Loan).filter(Loan.reader_id == current_user.id)
    if active_only:
        query = query.filter(Loan.return_date.is_(None))
    return query.order_by(Loan.id).all()


@router.get("/reader/{reader_id}/active", response_model=list[LoanOut])
def list_reader_active_loans(
    reader_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.LIBRARIAN and current_user.id != reader_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own active loans",
        )
    reader = db.get(User, reader_id)
    if reader is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reader not found")
    return _active_loans_query(db, reader_id).order_by(Loan.id).all()
