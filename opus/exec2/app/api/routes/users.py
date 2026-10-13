from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.deps import CurrentUser, DbSession, Now, PaginationParams, ensure_self_or_librarian, require_librarian
from app.models import User, UserRole
from app.schemas.common import ErrorResponse, Page
from app.schemas.loan import LoanRead
from app.schemas.user import UserRead
from app.services import loan_service, user_service

router = APIRouter(prefix="/users", tags=["Usuários"])

UserId = Annotated[int, Path(gt=0)]


@router.get("/me", response_model=UserRead, summary="Dados do usuário autenticado")
def read_me(current_user: CurrentUser) -> User:
    return current_user


@router.get(
    "/me/loans/active",
    response_model=list[LoanRead],
    summary="Meus empréstimos ativos",
    responses={400: {"model": ErrorResponse, "description": "O usuário autenticado não é leitor"}},
)
def read_my_active_loans(current_user: CurrentUser, db: DbSession, now: Now) -> list[LoanRead]:
    reader = user_service.get_reader(db, current_user.id)
    return [loan_service.build_loan_read(loan, now) for loan in loan_service.list_active_loans_for_reader(db, reader)]


@router.get(
    "",
    response_model=Page[UserRead],
    summary="Listar usuários",
    dependencies=[Depends(require_librarian)],
)
def list_users(
    db: DbSession,
    pagination: PaginationParams,
    role: Annotated[UserRole | None, Query(description="Filtra pelo tipo de usuário.")] = None,
) -> Page[UserRead]:
    users, total = user_service.list_users(db, role=role, skip=pagination.skip, limit=pagination.limit)
    return Page[UserRead](
        items=[UserRead.model_validate(user) for user in users],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Consultar usuário",
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def read_user(user_id: UserId, current_user: CurrentUser, db: DbSession) -> User:
    ensure_self_or_librarian(current_user, user_id)
    return user_service.get_user(db, user_id)


@router.get(
    "/{user_id}/loans/active",
    response_model=list[LoanRead],
    summary="Empréstimos ativos de um leitor",
    responses={
        400: {"model": ErrorResponse, "description": "O usuário não é leitor"},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def read_active_loans(user_id: UserId, current_user: CurrentUser, db: DbSession, now: Now) -> list[LoanRead]:
    """Bibliotecários consultam qualquer leitor; leitores, apenas a si mesmos.
    Empréstimos atrasados trazem a multa acumulada até hoje."""
    ensure_self_or_librarian(current_user, user_id)
    reader = user_service.get_reader(db, user_id)
    return [loan_service.build_loan_read(loan, now) for loan in loan_service.list_active_loans_for_reader(db, reader)]
