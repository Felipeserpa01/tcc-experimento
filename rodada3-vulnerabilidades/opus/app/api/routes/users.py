from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, Librarian, PageParams, Today, ensure_self_or_librarian
from app.models.user import UserRole
from app.schemas.common import Page
from app.schemas.loan import LoanRead
from app.schemas.user import UserRead
from app.services import loan_service, user_service

router = APIRouter(prefix="/users", tags=["Usuários"])


@router.get("/me", response_model=UserRead)
def read_me(current_user: CurrentUser) -> UserRead:
    return current_user


@router.get("", response_model=Page[UserRead])
def list_users(db: DbSession, _: Librarian, page: PageParams, role: UserRole | None = None) -> Page[UserRead]:
    users, total = user_service.list_users(db, role, page.skip, page.limit)
    return Page(items=users, total=total, skip=page.skip, limit=page.limit)


@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: int, db: DbSession, current_user: CurrentUser) -> UserRead:
    ensure_self_or_librarian(current_user, user_id)
    return user_service.get_user(db, user_id)


@router.get("/{user_id}/loans/active", response_model=list[LoanRead])
def list_active_loans(user_id: int, db: DbSession, current_user: CurrentUser, today: Today) -> list[LoanRead]:
    """Empréstimos ativos (não devolvidos) de um leitor, ordenados pela data prevista de devolução."""
    ensure_self_or_librarian(current_user, user_id)
    loans = loan_service.list_active_loans_for_reader(db, user_id)
    return [loan_service.build_loan_read(loan, today) for loan in loans]
