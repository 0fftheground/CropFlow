from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import get_administrative_division_query_service
from app.services import AdministrativeDivisionNode, AdministrativeDivisionQueryService

router = APIRouter(prefix="/administrative-divisions")


class AdministrativeDivisionNodeResponse(BaseModel):
    code: str
    adcode: str
    name: str
    division_type: str
    level: int
    parent_code: str | None
    has_children: bool
    is_virtual: bool


@router.get("", response_model=list[AdministrativeDivisionNodeResponse])
def list_administrative_division_children(
    parent_code: str | None = Query(default=None),
    parent_level: int | None = Query(default=None),
    service: AdministrativeDivisionQueryService = Depends(get_administrative_division_query_service),
) -> list[AdministrativeDivisionNodeResponse]:
    try:
        result = service.list_children(parent_code, parent_level=parent_level)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [_serialize_node(item) for item in result]


def _serialize_node(node: AdministrativeDivisionNode) -> AdministrativeDivisionNodeResponse:
    return AdministrativeDivisionNodeResponse(
        code=node.code,
        adcode=node.adcode,
        name=node.name,
        division_type=node.division_type,
        level=node.level,
        parent_code=node.parent_code,
        has_children=node.has_children,
        is_virtual=node.is_virtual,
    )
