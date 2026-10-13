from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ERROR_RESPONSES, Pagination, get_insurance_service, require, sorting
from app.core.pagination import SortParams
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.common import Page
from app.schemas.insurance import InsuranceCreate, InsuranceOut, InsuranceUpdate
from app.services.insurance_service import InsuranceService

router = APIRouter(prefix="/insurances", tags=["Convênios"], responses=ERROR_RESPONSES)

Insurances = Annotated[InsuranceService, Depends(get_insurance_service)]
InsuranceSort = Annotated[SortParams, Depends(sorting("name", "discount_percent", "created_at", default="name"))]


@router.post("", response_model=InsuranceOut, status_code=status.HTTP_201_CREATED, summary="Cadastrar convênio")
def create_insurance(
    data: InsuranceCreate,
    actor: Annotated[User, Depends(require(Permission.INSURANCES_MANAGE))],
    service: Insurances,
) -> object:
    return service.create(actor, data)


@router.get("", response_model=Page[InsuranceOut], summary="Listar convênios")
def list_insurances(
    _: Annotated[User, Depends(require(Permission.INSURANCES_READ))],
    service: Insurances,
    page: Pagination,
    sort: InsuranceSort,
    name: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    is_active: bool | None = True,
) -> object:
    return service.search(page, sort, name=name, is_active=is_active)


@router.get("/{insurance_id}", response_model=InsuranceOut, summary="Detalhar convênio")
def get_insurance(
    insurance_id: int, _: Annotated[User, Depends(require(Permission.INSURANCES_READ))], service: Insurances
) -> object:
    return service.get(insurance_id)


@router.patch("/{insurance_id}", response_model=InsuranceOut, summary="Atualizar convênio")
def update_insurance(
    insurance_id: int,
    data: InsuranceUpdate,
    actor: Annotated[User, Depends(require(Permission.INSURANCES_MANAGE))],
    service: Insurances,
) -> object:
    return service.update(actor, insurance_id, data)
