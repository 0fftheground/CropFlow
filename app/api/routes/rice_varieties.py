from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import get_rice_variety_query_service
from app.services import RiceVarietyOption, RiceVarietyQueryService

router = APIRouter(prefix="/rice-varieties")


class RiceVarietyOptionResponse(BaseModel):
    id: int
    name: str
    culti_type_code: int | None
    sub_type_code: int | None


@router.get("", response_model=list[RiceVarietyOptionResponse])
def search_rice_varieties(
    query: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    service: RiceVarietyQueryService = Depends(get_rice_variety_query_service),
) -> list[RiceVarietyOptionResponse]:
    try:
        result = service.search(query, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [_serialize_variety(item) for item in result]


def _serialize_variety(variety: RiceVarietyOption) -> RiceVarietyOptionResponse:
    return RiceVarietyOptionResponse(
        id=variety.id,
        name=variety.name,
        culti_type_code=variety.culti_type_code,
        sub_type_code=variety.sub_type_code,
    )
