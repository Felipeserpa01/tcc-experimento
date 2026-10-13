from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Librarian, Today, ensure_self_or_librarian
from app.models.user import User, UserRole
from app.schemas.loan import LoanOut
from app.schemas.user import UserCreate, UserOut
from app.services import loan_service, user_service

router = APIRouter(prefix="/users", tags=["Usuários"])

ACTIVE_ONLY = Query(True, description="Se verdadeiro, lista apenas empréstimos ainda não devolvidos")


@router.get("/me", response_model=UserOut, summary="Dados do usuário autenticado")
def read_me(current_user: CurrentUser) -> User:
    return current_user


@router.get("/me/loans", response_model=list[LoanOut], summary="Empréstimos do usuário autenticado")
def read_my_loans(
    current_user: CurrentUser,
    db: DbSession,
    today: Today,
    active_only: bool = ACTIVE_ONLY,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[LoanOut]:
    loans = loan_service.list_loans(
        db, today=today, reader_id=current_user.id, active_only=active_only, skip=skip, limit=limit
    )
    return [loan_service.build_loan_out(loan, today) for loan in loans]


@router.get("", response_model=list[UserOut], summary="Listar usuários (bibliotecário)")
def list_users(
    _: Librarian,
    db: DbSession,
    role: UserRole | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[User]:
    return user_service.list_users(db, role, skip, limit)


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar usuário de qualquer perfil (bibliotecário)",
    responses={409: {"description": "E-mail já cadastrado"}},
)
def create_user(data: UserCreate, _: Librarian, db: DbSession) -> User:
    return user_service.create_user(db, data, role=data.role)


@router.get("/{user_id}", response_model=UserOut, summary="Consultar usuário")
def read_user(user_id: int, current_user: CurrentUser, db: DbSession) -> User:
    ensure_self_or_librarian(current_user, user_id)
    return user_service.get_user(db, user_id)


@router.get(
    "/{user_id}/loans",
    response_model=list[LoanOut],
    summary="Empréstimos de um leitor (ativos por padrão)",
)
def read_user_loans(
    user_id: int,
    current_user: CurrentUser,
    db: DbSession,
    today: Today,
    active_only: bool = ACTIVE_ONLY,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[LoanOut]:
    ensure_self_or_librarian(current_user, user_id)
    user_service.get_user(db, user_id)
    loans = loan_service.list_loans(
        db, today=today, reader_id=user_id, active_only=active_only, skip=skip, limit=limit
    )
    return [loan_service.build_loan_out(loan, today) for loan in loans]
