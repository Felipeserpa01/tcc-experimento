from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.models.loan import Loan, LoanStatus
from app.models.book import Book
from app.models.user import User
from app.schemas.loan import LoanCreate, LoanResponse, LoanDetailResponse, LoanReturn
from app.security.jwt import get_current_user
from app.config import settings

router = APIRouter(prefix="/loans", tags=["loans"])

def calculate_fine(due_date: datetime, return_date: datetime) -> float:
    if return_date <= due_date:
        return 0.0

    days_late = (return_date - due_date).days
    return days_late * settings.LATE_FINE_PER_DAY

@router.post("/", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
async def create_loan(
    loan: LoanCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    book = db.query(Book).filter(Book.id == loan.book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    if book.available_quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No copies available for this book"
        )

    active_loans = db.query(Loan).filter(
        Loan.user_id == current_user["user_id"],
        Loan.status == LoanStatus.ACTIVE
    ).count()

    if active_loans >= settings.MAX_LOANS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum of {settings.MAX_LOANS_PER_USER} active loans reached"
        )

    due_date = datetime.utcnow() + timedelta(days=settings.LOAN_DURATION_DAYS)

    db_loan = Loan(
        user_id=current_user["user_id"],
        book_id=loan.book_id,
        due_date=due_date,
        status=LoanStatus.ACTIVE
    )

    book.available_quantity -= 1

    db.add(db_loan)
    db.add(book)
    db.commit()
    db.refresh(db_loan)

    return db_loan

@router.get("/user/active", response_model=list[LoanDetailResponse])
async def get_active_loans(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    loans = db.query(Loan).filter(
        Loan.user_id == current_user["user_id"],
        Loan.status == LoanStatus.ACTIVE
    ).all()

    result = []
    for loan in loans:
        book = db.query(Book).filter(Book.id == loan.book_id).first()
        loan_data = LoanResponse.model_validate(loan)
        result.append({
            **loan_data.model_dump(),
            "book_title": book.title if book else None,
            "user_username": current_user["username"]
        })

    return result

@router.post("/return", response_model=LoanResponse)
async def return_loan(
    loan_return: LoanReturn,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    loan_id = loan_return.loan_id
    loan = db.query(Loan).filter(Loan.id == loan_id).first()

    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found"
        )

    if loan.user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot return a loan that is not yours"
        )

    if loan.status != LoanStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active loans can be returned"
        )

    return_date = datetime.utcnow()
    loan.return_date = return_date
    loan.fine_amount = calculate_fine(loan.due_date, return_date)

    if return_date > loan.due_date:
        loan.status = LoanStatus.OVERDUE
    else:
        loan.status = LoanStatus.RETURNED

    book = db.query(Book).filter(Book.id == loan.book_id).first()
    if book:
        book.available_quantity += 1

    db.add(loan)
    if book:
        db.add(book)
    db.commit()
    db.refresh(loan)

    return loan

@router.get("/{loan_id}", response_model=LoanResponse)
async def get_loan(
    loan_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()

    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found"
        )

    if loan.user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view a loan that is not yours"
        )

    return loan

@router.get("/", response_model=list[LoanResponse])
async def list_all_loans(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    loans = db.query(Loan).offset(skip).limit(limit).all()
    return loans
