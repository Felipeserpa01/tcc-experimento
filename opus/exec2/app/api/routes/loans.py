from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import CurrentUser, DbSession, Now, PaginationParams, ensure_self_or_librarian, require_librarian
from app.core.exceptions import PermissionDeniedError
from app.models import LoanStatus, UserRole
from app.schemas.common import ErrorResponse, Page
from app.schemas.loan import LoanCreate, LoanRead
from app.services import loan_service
from app.utils.time import local_date

router = APIRouter(prefix="/loans", tags=["Empréstimos"])

LoanId = Annotated[int, Path(gt=0)]


@router.post(
    "",
    response_model=LoanRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar empréstimo",
    dependencies=[Depends(require_librarian)],
    responses={
        400: {"model": ErrorResponse, "description": "O usuário informado não é leitor"},
        404: {"model": ErrorResponse, "description": "Livro ou leitor não encontrado"},
        409: {"model": ErrorResponse, "description": "Sem exemplares disponíveis ou limite de empréstimos atingido"},
    },
)
def create_loan(data: LoanCreate, db: DbSession, now: Now) -> LoanRead:
    loan = loan_service.create_loan(db, data, now)
    return loan_service.build_loan_read(loan, now)


@router.post(
    "/{loan_id}/return",
    response_model=LoanRead,
    summary="Registrar devolução",
    dependencies=[Depends(require_librarian)],
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse, "description": "Empréstimo já devolvido"},
    },
)
def return_loan(loan_id: LoanId, db: DbSession, now: Now) -> LoanRead:
    """Registra a devolução na data atual e calcula a multa por atraso
    (dias após a data prevista x multa diária)."""
    loan = loan_service.return_loan(db, loan_id, now)
    return loan_service.build_loan_read(loan, now)


@router.get("", response_model=Page[LoanRead], summary="Listar empréstimos")
def list_loans(
    current_user: CurrentUser,
    db: DbSession,
    now: Now,
    pagination: PaginationParams,
    reader_id: Annotated[int | None, Query(gt=0)] = None,
    book_id: Annotated[int | None, Query(gt=0)] = None,
    status_filter: Annotated[
        LoanStatus | None,
        Query(alias="status", description="`active` inclui os atrasados; `overdue` traz apenas os atrasados."),
    ] = None,
) -> Page[LoanRead]:
    """Bibliotecários veem todos os empréstimos; leitores, apenas os próprios."""
    if current_user.role == UserRole.READER:
        if reader_id is not None and reader_id != current_user.id:
            raise PermissionDeniedError("Você só pode consultar os seus próprios empréstimos")
        reader_id = current_user.id

    loans, total = loan_service.list_loans(
        db,
        today=local_date(now),
        reader_id=reader_id,
        book_id=book_id,
        status=status_filter,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return Page[LoanRead](
        items=[loan_service.build_loan_read(loan, now) for loan in loans],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get(
    "/{loan_id}",
    response_model=LoanRead,
    summary="Consultar empréstimo",
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def read_loan(loan_id: LoanId, current_user: CurrentUser, db: DbSession, now: Now) -> LoanRead:
    loan = loan_service.get_loan(db, loan_id)
    ensure_self_or_librarian(current_user, loan.reader_id)
    return loan_service.build_loan_read(loan, now)
