from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import (
    get_farm_field_query_service,
    get_farm_field_service,
    get_farm_query_service,
    get_farm_service,
)
from app.db.session import get_db
from app.models import Farm, Field
from app.services.farms import UNSET
from app.services import (
    ConflictError,
    FarmCreateInput,
    FarmFieldQueryService,
    FarmFieldService,
    FarmQueryService,
    FarmService,
    FarmUpdateInput,
    FieldCreateInput,
    FieldUpdateInput,
)

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


class FieldCreateRequest(BaseModel):
    field_name: str
    external_field_id: str | None = None
    boundary_wkt: str | None = None
    centroid_lat: Decimal | None = None
    centroid_lon: Decimal | None = None
    area_ha: Decimal | None = None


class FieldUpdateRequest(BaseModel):
    field_name: str | None = None
    external_field_id: str | None = None
    boundary_wkt: str | None = None
    centroid_lat: Decimal | None = None
    centroid_lon: Decimal | None = None
    area_ha: Decimal | None = None


class FieldBatchCreateRequest(BaseModel):
    fields: list[FieldCreateRequest]


class FieldBatchDeleteRequest(BaseModel):
    field_ids: list[int]


class FieldResponse(BaseModel):
    id: str
    farm_id: int
    field_name: str
    external_field_id: str | None
    boundary_wkt: str | None
    centroid_lat: Decimal | None
    centroid_lon: Decimal | None
    area_ha: Decimal | None
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
                farm_name=_request_value(payload, "farm_name"),
                external_farm_id=_request_value(payload, "external_farm_id"),
                province=_request_value(payload, "province"),
                city=_request_value(payload, "city"),
                district_county=_request_value(payload, "district_county"),
                adcode=_request_value(payload, "adcode"),
                boundary_wkt=_request_value(payload, "boundary_wkt"),
                centroid_lat=_request_value(payload, "centroid_lat"),
                centroid_lon=_request_value(payload, "centroid_lon"),
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


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm(
    farm_id: int,
    service: FarmService = Depends(get_farm_service),
    db: Session = Depends(get_db),
) -> Response:
    try:
        service.delete(farm_id)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{farm_id}/fields", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
def create_field(
    farm_id: int,
    payload: FieldCreateRequest,
    service: FarmFieldService = Depends(get_farm_field_service),
    db: Session = Depends(get_db),
) -> FieldResponse:
    try:
        field = service.create(
            farm_id,
            FieldCreateInput(
                field_name=payload.field_name,
                external_field_id=payload.external_field_id,
                boundary_wkt=payload.boundary_wkt,
                centroid_lat=payload.centroid_lat,
                centroid_lon=payload.centroid_lon,
                area_ha=payload.area_ha,
            ),
        )
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return _serialize_field(farm_id, field)


@router.post("/{farm_id}/fields/batch", response_model=list[FieldResponse], status_code=status.HTTP_201_CREATED)
def create_fields_batch(
    farm_id: int,
    payload: FieldBatchCreateRequest,
    service: FarmFieldService = Depends(get_farm_field_service),
    db: Session = Depends(get_db),
) -> list[FieldResponse]:
    try:
        fields = service.create_batch(
            farm_id,
            [
                FieldCreateInput(
                    field_name=item.field_name,
                    external_field_id=item.external_field_id,
                    boundary_wkt=item.boundary_wkt,
                    centroid_lat=item.centroid_lat,
                    centroid_lon=item.centroid_lon,
                    area_ha=item.area_ha,
                )
                for item in payload.fields
            ],
        )
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return [_serialize_field(farm_id, item) for item in fields]


@router.get("/{farm_id}/fields", response_model=list[FieldResponse])
def list_fields(
    farm_id: int,
    service: FarmFieldQueryService = Depends(get_farm_field_query_service),
) -> list[FieldResponse]:
    try:
        fields = service.list_by_farm(farm_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [_serialize_field(farm_id, item) for item in fields]


@router.get("/{farm_id}/fields/{field_id}", response_model=FieldResponse)
def get_field(
    farm_id: int,
    field_id: int,
    service: FarmFieldQueryService = Depends(get_farm_field_query_service),
) -> FieldResponse:
    try:
        field = service.get(farm_id, field_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _serialize_field(farm_id, field)


@router.patch("/{farm_id}/fields/{field_id}", response_model=FieldResponse)
def update_field(
    farm_id: int,
    field_id: int,
    payload: FieldUpdateRequest,
    service: FarmFieldService = Depends(get_farm_field_service),
    db: Session = Depends(get_db),
) -> FieldResponse:
    try:
        field = service.update(
            farm_id,
            field_id,
            FieldUpdateInput(
                field_name=_request_value(payload, "field_name"),
                external_field_id=_request_value(payload, "external_field_id"),
                boundary_wkt=_request_value(payload, "boundary_wkt"),
                centroid_lat=_request_value(payload, "centroid_lat"),
                centroid_lon=_request_value(payload, "centroid_lon"),
                area_ha=_request_value(payload, "area_ha"),
            ),
        )
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return _serialize_field(farm_id, field)


@router.delete("/{farm_id}/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field(
    farm_id: int,
    field_id: int,
    service: FarmFieldService = Depends(get_farm_field_service),
    db: Session = Depends(get_db),
) -> Response:
    try:
        service.delete(farm_id, field_id)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{farm_id}/fields/batch-delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_fields_batch(
    farm_id: int,
    payload: FieldBatchDeleteRequest,
    service: FarmFieldService = Depends(get_farm_field_service),
    db: Session = Depends(get_db),
) -> Response:
    try:
        service.delete_batch(farm_id, payload.field_ids)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


def _serialize_field(farm_id: int, field: Field) -> FieldResponse:
    return FieldResponse(
        id=str(field.id),
        farm_id=farm_id,
        field_name=field.field_name,
        external_field_id=field.external_field_id,
        boundary_wkt=field.boundary_wkt,
        centroid_lat=field.centroid_lat,
        centroid_lon=field.centroid_lon,
        area_ha=field.area_ha,
        created_at=field.created_at,
        updated_at=field.updated_at,
    )


def _request_value(payload: BaseModel, field_name: str):
    return getattr(payload, field_name) if field_name in payload.model_fields_set else UNSET
