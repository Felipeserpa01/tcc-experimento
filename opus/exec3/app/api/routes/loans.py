from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Librarian, Today, ensure_self_or_librarian
from app.schemas.loan import LoanCreate, LoanOut
from app.services import loan_service

router = APIRouter(prefix="/loans", tags=["Empréstimos"])


@router.post(
    "",
    response_model=LoanOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar empréstimo (bibliotecário)",
    responses={
        404: {"description": "Livro ou leitor não encontrado"},
        409: {"description": "Sem exemplares disponíveis ou limite de empréstimos atingido"},
        422: {"description": "Dados inválidos ou usuário não é leitor"},
    },
)
def create_loan(data: LoanCreate, _: Librarian, db: DbSession, today: Today) -> LoanOut:
    loan = loan_service.create_loan(db, data, today)
    return loan_service.build_loan_out(loan, today)


@router.get("", response_model=list[LoanOut], summary="Listar empréstimos (bibliotecário)")
def list_loans(
    _: Librarian,
    db: DbSession,
    today: Today,
    reader_id: int | None = Query(None, gt=0),
    book_id: int | None = Query(None, gt=0),
    active_only: bool = Query(False, description="Apenas empréstimos não devolvidos"),
    overdue_only: bool = Query(False, description="Apenas empréstimos ativos com prazo vencido"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[LoanOut]:
    loans = loan_service.list_loans(
        db,
        today=today,
        reader_id=reader_id,
        book_id=book_id,
        active_only=active_only,
        overdue_only=overdue_only,
        skip=skip,
        limit=limit,
    )
    return [loan_service.build_loan_out(loan, today) for loan in loans]


@router.get("/{loan_id}", response_model=LoanOut, summary="Consultar empréstimo")
def read_loan(loan_id: int, current_user: CurrentUser, db: DbSession, today: Today) -> LoanOut:
    loan = loan_service.get_loan(db, loan_id)
    ensure_self_or_librarian(current_user, loan.reader_id)
    return loan_service.build_loan_out(loan, today)


@router.post(
    "/{loan_id}/return",
    response_model=LoanOut,
    summary="Registrar devolução e calcular multa (bibliotecário)",
    responses={404: {"description": "Empréstimo não encontrado"}, 409: {"description": "Empréstimo já devolvido"}},
)
def return_loan(loan_id: int, _: Librarian, db: DbSession, today: Today) -> LoanOut:
    """A data de devolução é a data atual; a multa é `dias de atraso x DAILY_FINE`."""
    loan = loan_service.return_loan(db, loan_id, today)
    return loan_service.build_loan_out(loan, today)
