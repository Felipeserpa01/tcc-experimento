from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.models import Loan, Book, User
from app.schemas import LoanCreate, LoanResponse, LoanReturnRequest
from app.dependencies import get_current_user, get_current_librarian
from app.core.config import LOAN_DAYS, LATE_FEE_PER_DAY, MAX_LOANS_PER_USER

router = APIRouter(prefix="/api/loans", tags=["loans"])


def calculate_fine(due_date: datetime, return_date: datetime) -> float:
    days_late = (return_date - due_date).days
    if days_late <= 0:
        return 0.0
    return days_late * LATE_FEE_PER_DAY


@router.post("/", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
async def create_loan(
    loan_data: LoanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    active_loans = db.query(Loan).filter(
        Loan.user_id == current_user.id,
        Loan.return_date == None
    ).count()

    if active_loans >= MAX_LOANS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite de {MAX_LOANS_PER_USER} empréstimos simultâneos atingido",
        )

    book = db.query(Book).filter(Book.id == loan_data.book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro não encontrado",
        )

    if book.available_quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum exemplar disponível deste livro",
        )

    due_date = datetime.now(timezone.utc) + timedelta(days=LOAN_DAYS)

    db_loan = Loan(
        user_id=current_user.id,
        book_id=loan_data.book_id,
        due_date=due_date,
    )

    book.available_quantity -= 1

    db.add(db_loan)
    db.commit()
    db.refresh(db_loan)
    return db_loan


@router.get("/", response_model=list[LoanResponse])
async def list_loans(
    current_user: User = Depends(get_current_librarian),
    db: Session = Depends(get_db),
):
    loans = db.query(Loan).all()
    return loans


@router.get("/my-loans", response_model=list[LoanResponse])
async def get_my_loans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loans = db.query(Loan).filter(Loan.user_id == current_user.id).all()
    return loans


@router.get("/active-loans/{user_id}", response_model=list[LoanResponse])
async def get_active_loans(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.id != user_id and not current_user.is_librarian:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar os empréstimos de outro usuário",
        )

    loans = db.query(Loan).filter(
        Loan.user_id == user_id,
        Loan.return_date == None
    ).all()
    return loans


@router.post("/{loan_id}/return", response_model=LoanResponse)
async def return_loan(
    loan_id: int,
    return_request: LoanReturnRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empréstimo não encontrado",
        )

    if loan.return_date is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este livro já foi devolvido",
        )

    if loan.user_id != current_user.id and not current_user.is_librarian:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não pode devolver o empréstimo de outro usuário",
        )

    loan.return_date = return_request.return_date
    loan.fine = calculate_fine(loan.due_date, return_request.return_date)

    book = db.query(Book).filter(Book.id == loan.book_id).first()
    book.available_quantity += 1

    db.commit()
    db.refresh(loan)
    return loan


@router.get("/{loan_id}", response_model=LoanResponse)
async def get_loan(
    loan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empréstimo não encontrado",
        )

    if loan.user_id != current_user.id and not current_user.is_librarian:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este empréstimo",
        )

    return loan
