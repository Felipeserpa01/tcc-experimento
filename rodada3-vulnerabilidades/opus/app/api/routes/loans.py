from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Librarian, PageParams, Today, ensure_self_or_librarian
from app.schemas.common import ErrorResponse, Page
from app.schemas.loan import FineRead, LoanCreate, LoanRead, LoanStatus
from app.services import loan_service

router = APIRouter(prefix="/loans", tags=["Empréstimos"])

NOT_FOUND = {404: {"model": ErrorResponse}}


@router.post(
    "",
    response_model=LoanRead,
    status_code=status.HTTP_201_CREATED,
    responses={**NOT_FOUND, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_loan(data: LoanCreate, db: DbSession, _: Librarian, today: Today) -> LoanRead:
    """Registra o empréstimo de um livro a um leitor.

    Regras: o livro precisa ter exemplar disponível (409 `book_unavailable`) e o leitor pode ter
    no máximo o limite configurado de empréstimos simultâneos (409 `loan_limit_reached`).
    """
    loan = loan_service.create_loan(db, data, today)
    return loan_service.build_loan_read(loan, today)


@router.get("", response_model=Page[LoanRead])
def list_loans(
    db: DbSession,
    current_user: CurrentUser,
    today: Today,
    page: PageParams,
    reader_id: Annotated[int | None, Query(gt=0)] = None,
    status_filter: Annotated[LoanStatus | None, Query(alias="status")] = None,
    overdue: Annotated[bool, Query(description="Somente empréstimos ativos com devolução atrasada")] = False,
) -> Page[LoanRead]:
    """Lista empréstimos. Bibliotecários veem todos; leitores veem apenas os próprios."""
    if not current_user.is_librarian:
        if reader_id is not None:
            ensure_self_or_librarian(current_user, reader_id)
        reader_id = current_user.id

    loans, total = loan_service.list_loans(
        db,
        today,
        reader_id=reader_id,
        status=status_filter,
        overdue_only=overdue,
        skip=page.skip,
        limit=page.limit,
    )
    items = [loan_service.build_loan_read(loan, today) for loan in loans]
    return Page(items=items, total=total, skip=page.skip, limit=page.limit)


@router.get("/{loan_id}", response_model=LoanRead, responses=NOT_FOUND)
def read_loan(loan_id: int, db: DbSession, current_user: CurrentUser, today: Today) -> LoanRead:
    loan = loan_service.get_loan(db, loan_id)
    ensure_self_or_librarian(current_user, loan.reader_id)
    return loan_service.build_loan_read(loan, today)


@router.post(
    "/{loan_id}/return",
    response_model=LoanRead,
    responses={**NOT_FOUND, 409: {"model": ErrorResponse}},
)
def return_loan(loan_id: int, db: DbSession, _: Librarian, today: Today) -> LoanRead:
    """Registra a devolução com a data atual e calcula a multa por atraso, se houver."""
    loan = loan_service.return_loan(db, loan_id, today)
    return loan_service.build_loan_read(loan, today)


@router.get("/{loan_id}/fine", response_model=FineRead, responses=NOT_FOUND)
def read_fine(loan_id: int, db: DbSession, current_user: CurrentUser, today: Today) -> FineRead:
    """Multa por atraso: definitiva se já devolvido, ou acumulada até hoje se ainda ativo."""
    loan = loan_service.get_loan(db, loan_id)
    ensure_self_or_librarian(current_user, loan.reader_id)
    return loan_service.build_fine(loan, today)
