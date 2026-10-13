from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_user, require_librarian

router = APIRouter(prefix="/loans", tags=["Empréstimos"])

LOAN_PERIOD_DAYS = 14
MAX_ACTIVE_LOANS = 3
FINE_PER_DAY = 1.0


def _calculate_fine(due_date: datetime, return_date: datetime) -> float:
    days_late = (return_date.date() - due_date.date()).days
    if days_late <= 0:
        return 0.0
    return round(days_late * FINE_PER_DAY, 2)


@router.post("/", response_model=schemas.LoanOut, status_code=status.HTTP_201_CREATED)
def create_loan(
    loan_in: schemas.LoanCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_librarian),
):
    reader = db.query(models.User).filter(models.User.id == loan_in.reader_id).first()
    if not reader:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leitor não encontrado")
    if reader.role != models.UserRole.READER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empréstimos só podem ser registrados para usuários do tipo leitor",
        )

    book = db.query(models.Book).filter(models.Book.id == loan_in.book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Livro não encontrado")

    if book.available_quantity < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não há exemplares disponíveis deste livro",
        )

    active_count = (
        db.query(models.Loan)
        .filter(models.Loan.reader_id == reader.id, models.Loan.return_date.is_(None))
        .count()
    )
    if active_count >= MAX_ACTIVE_LOANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Leitor já possui o máximo de {MAX_ACTIVE_LOANS} empréstimos ativos",
        )

    now = datetime.utcnow()
    loan = models.Loan(
        book_id=book.id,
        reader_id=reader.id,
        loan_date=now,
        due_date=now + timedelta(days=LOAN_PERIOD_DAYS),
    )
    book.available_quantity -= 1

    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


@router.post("/{loan_id}/return", response_model=schemas.LoanOut)
def return_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_librarian),
):
    loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empréstimo não encontrado"
        )
    if loan.return_date is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Este empréstimo já foi devolvido"
        )

    now = datetime.utcnow()
    loan.return_date = now
    loan.fine_amount = _calculate_fine(loan.due_date, now)

    book = db.query(models.Book).filter(models.Book.id == loan.book_id).first()
    book.available_quantity += 1

    db.commit()
    db.refresh(loan)
    return loan


@router.get("/", response_model=List[schemas.LoanOut])
def list_loans(
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_librarian),
):
    query = db.query(models.Loan)
    if active_only:
        query = query.filter(models.Loan.return_date.is_(None))
    return query.order_by(models.Loan.id).all()


@router.get("/me", response_model=List[schemas.LoanOut])
def list_my_loans(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Loan).filter(models.Loan.reader_id == current_user.id)
    if active_only:
        query = query.filter(models.Loan.return_date.is_(None))
    return query.order_by(models.Loan.id).all()


@router.get("/reader/{reader_id}", response_model=List[schemas.LoanOut])
def list_reader_loans(
    reader_id: int,
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != models.UserRole.LIBRARIAN and current_user.id != reader_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")

    reader = db.query(models.User).filter(models.User.id == reader_id).first()
    if not reader:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leitor não encontrado")

    query = db.query(models.Loan).filter(models.Loan.reader_id == reader_id)
    if active_only:
        query = query.filter(models.Loan.return_date.is_(None))
    return query.order_by(models.Loan.id).all()
