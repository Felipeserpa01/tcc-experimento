from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import verify_token
from app.schemas.loan import LoanCreate, LoanReturn, LoanResponse
from app.crud.loan import (
    create_loan, get_active_loans, get_loan_by_id, return_loan, get_loans_count
)

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("/", response_model=LoanResponse)
def borrow_book(
    loan: LoanCreate,
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    if token["role"] != "reader":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only readers can borrow books"
        )

    active_loans_count = get_loans_count(db, reader_id=token["user_id"])
    if active_loans_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reader cannot have more than 3 active loans"
        )

    db_loan = create_loan(db, reader_id=token["user_id"], loan=loan)

    if db_loan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    if db_loan is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No copies available of this book"
        )

    return db_loan


@router.get("/", response_model=list[LoanResponse])
def list_active_loans(
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    if token["role"] != "reader":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only readers can list their loans"
        )

    return get_active_loans(db, reader_id=token["user_id"])


@router.post("/{loan_id}/return", response_model=LoanResponse)
def return_book(
    loan_id: int,
    loan: LoanReturn,
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    db_loan = get_loan_by_id(db, loan_id)

    if not db_loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found"
        )

    if db_loan.reader_id != token["user_id"] and token["role"] != "librarian":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only return your own loans"
        )

    if db_loan.return_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This book has already been returned"
        )

    returned_loan = return_loan(db, loan_id, loan.return_date)
    return returned_loan
