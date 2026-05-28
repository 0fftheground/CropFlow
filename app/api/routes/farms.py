from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_farm_query_service, get_farm_service
from app.db.session import get_db
from app.models import Farm
from app.services import FarmCreateInput, FarmQueryService, FarmService, FarmUpdateInput

router = APIRouter(prefix="/farms")


class FarmCreateRequest(BaseModel):
    farm_name: str
    external_farm_id: str | None = None
    province: str
    city: str
    district_county: str
    adcode: str
    boundary_wkt: str | None = None
    centroid_lat: Decimal | None = None
    centroid_lon: Decimal | None = None


class FarmUpdateRequest(BaseModel):
    farm_name: str | None = None
    external_farm_id: str | None = None
    province: str | None = None
    city: str | None = None
    district_county: str | None = None
    adcode: str | None = None
    boundary_wkt: str | None = None
    centroid_lat: Decimal | None = None
    centroid_lon: Decimal | None = None


class FarmResponse(BaseModel):
    id: int
    farm_name: str
    external_farm_id: str | None
    province: str | None
    city: str | None
    district_county: str | None
    adcode: str | None
    boundary_wkt: str | None
    centroid_lat: Decimal | None
    centroid_lon: Decimal | None
    created_at: datetime | None
    updated_at: datetime | None


@router.post("", response_model=FarmResponse, status_code=status.HTTP_201_CREATED)
def create_farm(
    payload: FarmCreateRequest,
    service: FarmService = Depends(get_farm_service),
    db: Session = Depends(get_db),
) -> FarmResponse:
    try:
        farm = service.create(
            FarmCreateInput(
                farm_name=payload.farm_name,
                external_farm_id=payload.external_farm_id,
                province=payload.province,
                city=payload.city,
                district_county=payload.district_county,
                adcode=payload.adcode,
                boundary_wkt=payload.boundary_wkt,
                centroid_lat=payload.centroid_lat,
                centroid_lon=payload.centroid_lon,
            ),
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return _serialize_farm(farm)


@router.get("", response_model=list[FarmResponse])
def list_farms(
    service: FarmQueryService = Depends(get_farm_query_service),
) -> list[FarmResponse]:
    return [_serialize_farm(item) for item in service.list_all()]


@router.get("/{farm_id}", response_model=FarmResponse)
def get_farm(
    farm_id: int,
    service: FarmQueryService = Depends(get_farm_query_service),
) -> FarmResponse:
    try:
        farm = service.get(farm_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _serialize_farm(farm)


@router.patch("/{farm_id}", response_model=FarmResponse)
def update_farm(
    farm_id: int,
    payload: FarmUpdateRequest,
    service: FarmService = Depends(get_farm_service),
    db: Session = Depends(get_db),
) -> FarmResponse:
    try:
        farm = service.update(
            farm_id,
            FarmUpdateInput(
                farm_name=payload.farm_name,
                external_farm_id=payload.external_farm_id,
                province=payload.province,
                city=payload.city,
                district_county=payload.district_county,
                adcode=payload.adcode,
                boundary_wkt=payload.boundary_wkt,
                centroid_lat=payload.centroid_lat,
                centroid_lon=payload.centroid_lon,
            ),
        )
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return _serialize_farm(farm)


def _serialize_farm(farm: Farm) -> FarmResponse:
    return FarmResponse(
        id=farm.id,
        farm_name=farm.farm_name,
        external_farm_id=farm.external_farm_id,
        province=farm.province,
        city=farm.city,
        district_county=farm.district_county,
        adcode=farm.adcode,
        boundary_wkt=farm.boundary_wkt,
        centroid_lat=farm.centroid_lat,
        centroid_lon=farm.centroid_lon,
        created_at=farm.created_at,
        updated_at=farm.updated_at,
    )
