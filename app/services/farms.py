from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.models import Farm
from app.repositories import FarmRepository


@dataclass(slots=True)
class FarmCreateInput:
    farm_name: str
    province: str
    city: str
    district_county: str
    adcode: str
    external_farm_id: str | None = None
    boundary_wkt: str | None = None
    centroid_lat: Decimal | None = None
    centroid_lon: Decimal | None = None


@dataclass(slots=True)
class FarmUpdateInput:
    farm_name: str | None = None
    external_farm_id: str | None = None
    province: str | None = None
    city: str | None = None
    district_county: str | None = None
    adcode: str | None = None
    boundary_wkt: str | None = None
    centroid_lat: Decimal | None = None
    centroid_lon: Decimal | None = None


class FarmService:
    def __init__(self, farm_repository: FarmRepository) -> None:
        self.farm_repository = farm_repository

    def create(self, payload: FarmCreateInput) -> Farm:
        farm = Farm(
            farm_name=_require_non_empty(payload.farm_name, "farm_name"),
            external_farm_id=_normalize_optional_string(payload.external_farm_id),
            province=_require_non_empty(payload.province, "province"),
            city=_require_non_empty(payload.city, "city"),
            district_county=_require_non_empty(payload.district_county, "district_county"),
            adcode=_require_non_empty(payload.adcode, "adcode"),
            boundary_wkt=_normalize_optional_string(payload.boundary_wkt),
            centroid_lat=payload.centroid_lat,
            centroid_lon=payload.centroid_lon,
            created_by_type="user",
            created_by_id="api",
        )
        self.farm_repository.add(farm)
        self.farm_repository.flush()
        return farm

    def update(self, farm_id: int, payload: FarmUpdateInput) -> Farm:
        farm = self.farm_repository.get(farm_id)
        if farm is None:
            raise LookupError(f"Farm {farm_id} does not exist.")

        if payload.farm_name is not None:
            farm.farm_name = _require_non_empty(payload.farm_name, "farm_name")
        if payload.external_farm_id is not None:
            farm.external_farm_id = _require_non_empty(payload.external_farm_id, "external_farm_id")
        if payload.province is not None:
            farm.province = _require_non_empty(payload.province, "province")
        if payload.city is not None:
            farm.city = _require_non_empty(payload.city, "city")
        if payload.district_county is not None:
            farm.district_county = _require_non_empty(payload.district_county, "district_county")
        if payload.adcode is not None:
            farm.adcode = _require_non_empty(payload.adcode, "adcode")
        if payload.boundary_wkt is not None:
            farm.boundary_wkt = _normalize_optional_string(payload.boundary_wkt)
        if payload.centroid_lat is not None:
            farm.centroid_lat = payload.centroid_lat
        if payload.centroid_lon is not None:
            farm.centroid_lon = payload.centroid_lon
        farm.updated_at = _utcnow()
        return farm


class FarmQueryService:
    def __init__(self, farm_repository: FarmRepository) -> None:
        self.farm_repository = farm_repository

    def get(self, farm_id: int) -> Farm:
        farm = self.farm_repository.get(farm_id)
        if farm is None:
            raise LookupError(f"Farm {farm_id} does not exist.")
        return farm

    def list_all(self) -> list[Farm]:
        return self.farm_repository.list_all()


def _require_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required.")
    return normalized


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
