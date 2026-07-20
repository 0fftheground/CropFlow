from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.models import Farm, Field
from app.repositories import (
    FarmFieldRelationRepository,
    FarmRepository,
    FieldRepository,
    PlantingPlanFieldRelationRepository,
    PlantingPlanRepository,
)


class ConflictError(Exception):
    pass


UNSET = object()


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
    farm_name: Any = UNSET
    external_farm_id: Any = UNSET
    province: Any = UNSET
    city: Any = UNSET
    district_county: Any = UNSET
    adcode: Any = UNSET
    boundary_wkt: Any = UNSET
    centroid_lat: Any = UNSET
    centroid_lon: Any = UNSET


@dataclass(slots=True)
class FieldCreateInput:
    field_name: str
    external_field_id: str | None = None
    boundary_wkt: str | None = None
    centroid_lat: Decimal | None = None
    centroid_lon: Decimal | None = None
    area_ha: Decimal | None = None


@dataclass(slots=True)
class FieldUpdateInput:
    field_name: Any = UNSET
    external_field_id: Any = UNSET
    boundary_wkt: Any = UNSET
    centroid_lat: Any = UNSET
    centroid_lon: Any = UNSET
    area_ha: Any = UNSET


class FarmService:
    def __init__(
        self,
        farm_repository: FarmRepository,
        *,
        field_repository: FieldRepository | None = None,
        farm_field_relation_repository: FarmFieldRelationRepository | None = None,
        planting_plan_repository: PlantingPlanRepository | None = None,
        planting_plan_field_relation_repository: PlantingPlanFieldRelationRepository | None = None,
    ) -> None:
        self.farm_repository = farm_repository
        self.field_repository = field_repository
        self.farm_field_relation_repository = farm_field_relation_repository
        self.planting_plan_repository = planting_plan_repository
        self.planting_plan_field_relation_repository = planting_plan_field_relation_repository

    def create(self, payload: FarmCreateInput) -> Farm:
        external_farm_id = _normalize_optional_string(payload.external_farm_id)
        self._ensure_external_farm_id_available(external_farm_id)
        centroid_lat = _validate_latitude(payload.centroid_lat, field_name="centroid_lat")
        centroid_lon = _validate_longitude(payload.centroid_lon, field_name="centroid_lon")

        farm = Farm(
            farm_name=_require_non_empty(payload.farm_name, "farm_name"),
            external_farm_id=external_farm_id,
            province=_require_non_empty(payload.province, "province"),
            city=_require_non_empty(payload.city, "city"),
            district_county=_require_non_empty(payload.district_county, "district_county"),
            adcode=_require_non_empty(payload.adcode, "adcode"),
            boundary_wkt=_normalize_optional_string(payload.boundary_wkt),
            centroid_lat=centroid_lat,
            centroid_lon=centroid_lon,
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

        if payload.farm_name is not UNSET:
            farm.farm_name = _require_required_update_string(payload.farm_name, "farm_name")
        if payload.external_farm_id is not UNSET:
            external_farm_id = _normalize_optional_string(payload.external_farm_id)
            self._ensure_external_farm_id_available(external_farm_id, current_farm_id=farm_id)
            farm.external_farm_id = external_farm_id
        if payload.province is not UNSET:
            farm.province = _require_required_update_string(payload.province, "province")
        if payload.city is not UNSET:
            farm.city = _require_required_update_string(payload.city, "city")
        if payload.district_county is not UNSET:
            farm.district_county = _require_required_update_string(payload.district_county, "district_county")
        if payload.adcode is not UNSET:
            farm.adcode = _require_required_update_string(payload.adcode, "adcode")
        if payload.boundary_wkt is not UNSET:
            farm.boundary_wkt = _normalize_optional_string(payload.boundary_wkt)
        if payload.centroid_lat is not UNSET:
            farm.centroid_lat = _validate_latitude(payload.centroid_lat, field_name="centroid_lat")
        if payload.centroid_lon is not UNSET:
            farm.centroid_lon = _validate_longitude(payload.centroid_lon, field_name="centroid_lon")
        farm.updated_at = _utcnow()
        return farm

    def delete(self, farm_id: int) -> None:
        farm = self.farm_repository.get(farm_id)
        if farm is None:
            raise LookupError(f"Farm {farm_id} does not exist.")
        if self.planting_plan_repository is not None and self.planting_plan_repository.exists_by_farm_id(farm_id):
            raise ConflictError(f"Farm {farm_id} is referenced by planting plans and cannot be deleted.")

        field_ids = (
            self.farm_field_relation_repository.list_field_ids_by_farm(farm_id)
            if self.farm_field_relation_repository is not None
            else []
        )
        if (
            self.planting_plan_field_relation_repository is not None
            and self.planting_plan_field_relation_repository.list_linked_field_ids(field_ids)
        ):
            raise ConflictError(f"Farm {farm_id} has fields referenced by planting plans and cannot be deleted.")

        if self.farm_field_relation_repository is not None:
            for field_id in field_ids:
                if (
                    self.field_repository is not None
                    and self.farm_field_relation_repository.count_by_field(field_id) == 1
                ):
                    field = self.field_repository.get(field_id)
                    if field is not None:
                        self.field_repository.delete(field)
            self.farm_field_relation_repository.delete_by_farm(farm_id)

        self.farm_repository.delete(farm)

    def _ensure_external_farm_id_available(
        self,
        external_farm_id: str | None,
        *,
        current_farm_id: int | None = None,
    ) -> None:
        if external_farm_id is None:
            return
        existing = self.farm_repository.get_by_external_farm_id(external_farm_id)
        if existing is not None and existing.id != current_farm_id:
            raise ValueError(f"external_farm_id {external_farm_id} already exists.")


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


class FarmFieldService:
    def __init__(
        self,
        field_repository: FieldRepository,
        farm_repository: FarmRepository,
        farm_field_relation_repository: FarmFieldRelationRepository,
        *,
        planting_plan_field_relation_repository: PlantingPlanFieldRelationRepository | None = None,
    ) -> None:
        self.field_repository = field_repository
        self.farm_repository = farm_repository
        self.farm_field_relation_repository = farm_field_relation_repository
        self.planting_plan_field_relation_repository = planting_plan_field_relation_repository

    def create(self, farm_id: int, payload: FieldCreateInput) -> Field:
        self._get_farm(farm_id)
        external_field_id = _normalize_optional_string(payload.external_field_id)
        self._ensure_external_field_id_available(farm_id, external_field_id)
        centroid_lat = _validate_latitude(payload.centroid_lat, field_name="centroid_lat")
        centroid_lon = _validate_longitude(payload.centroid_lon, field_name="centroid_lon")
        area_ha = _validate_area_ha(payload.area_ha)

        field = Field(
            field_name=_require_non_empty(payload.field_name, "field_name"),
            external_field_id=external_field_id,
            boundary_wkt=_normalize_optional_string(payload.boundary_wkt),
            centroid_lat=centroid_lat,
            centroid_lon=centroid_lon,
            area_ha=area_ha,
            created_by_type="user",
            created_by_id="api",
        )
        self.field_repository.add(field)
        self.field_repository.flush()
        self.farm_field_relation_repository.create(farm_id, field.id)
        self.farm_field_relation_repository.flush()
        return field

    def create_batch(self, farm_id: int, payloads: list[FieldCreateInput]) -> list[Field]:
        self._get_farm(farm_id)
        if not payloads:
            raise ValueError("fields is required.")

        normalized_external_ids: list[str | None] = []
        for payload in payloads:
            _require_non_empty(payload.field_name, "field_name")
            normalized_external_ids.append(_normalize_optional_string(payload.external_field_id))

        duplicate_external_ids = _find_duplicate_strings(normalized_external_ids)
        if duplicate_external_ids:
            raise ValueError(f"Duplicate external_field_id values in batch: {duplicate_external_ids}.")
        for external_field_id in normalized_external_ids:
            self._ensure_external_field_id_available(farm_id, external_field_id)

        fields: list[Field] = []
        for payload, external_field_id in zip(payloads, normalized_external_ids, strict=False):
            field = Field(
                field_name=_require_non_empty(payload.field_name, "field_name"),
                external_field_id=external_field_id,
                boundary_wkt=_normalize_optional_string(payload.boundary_wkt),
                centroid_lat=_validate_latitude(payload.centroid_lat, field_name="centroid_lat"),
                centroid_lon=_validate_longitude(payload.centroid_lon, field_name="centroid_lon"),
                area_ha=_validate_area_ha(payload.area_ha),
                created_by_type="user",
                created_by_id="api",
            )
            self.field_repository.add(field)
            self.field_repository.flush()
            self.farm_field_relation_repository.create(farm_id, field.id)
            fields.append(field)

        self.farm_field_relation_repository.flush()
        return fields

    def update(self, farm_id: int, field_id: int, payload: FieldUpdateInput) -> Field:
        field = self._get_field_in_farm(farm_id, field_id)

        if payload.field_name is not UNSET:
            field.field_name = _require_required_update_string(payload.field_name, "field_name")
        if payload.external_field_id is not UNSET:
            external_field_id = _normalize_optional_string(payload.external_field_id)
            self._ensure_external_field_id_available(farm_id, external_field_id, current_field_id=field_id)
            field.external_field_id = external_field_id
        if payload.boundary_wkt is not UNSET:
            field.boundary_wkt = _normalize_optional_string(payload.boundary_wkt)
        if payload.centroid_lat is not UNSET:
            field.centroid_lat = _validate_latitude(payload.centroid_lat, field_name="centroid_lat")
        if payload.centroid_lon is not UNSET:
            field.centroid_lon = _validate_longitude(payload.centroid_lon, field_name="centroid_lon")
        if payload.area_ha is not UNSET:
            field.area_ha = _validate_area_ha(payload.area_ha)
        field.updated_at = _utcnow()
        return field

    def delete(self, farm_id: int, field_id: int) -> None:
        relation = self.farm_field_relation_repository.get_by_farm_field(farm_id, field_id)
        if relation is None:
            raise LookupError(f"Field {field_id} does not exist in farm {farm_id}.")
        if (
            self.planting_plan_field_relation_repository is not None
            and self.planting_plan_field_relation_repository.list_linked_field_ids([field_id])
        ):
            raise ConflictError(f"Field {field_id} is referenced by planting plans and cannot be deleted.")

        field = self.field_repository.get(field_id)
        if field is None:
            raise LookupError(f"Field {field_id} does not exist.")

        relation_count = self.farm_field_relation_repository.count_by_field(field_id)
        self.farm_field_relation_repository.delete(relation)
        if relation_count <= 1:
            self.field_repository.delete(field)

    def delete_batch(self, farm_id: int, field_ids: list[int]) -> None:
        self._get_farm(farm_id)
        if not field_ids:
            raise ValueError("field_ids is required.")

        normalized_field_ids = sorted(set(field_ids))
        missing_field_ids: list[int] = []
        for field_id in normalized_field_ids:
            if self.farm_field_relation_repository.get_by_farm_field(farm_id, field_id) is None:
                missing_field_ids.append(field_id)
        if missing_field_ids:
            raise LookupError(f"Fields {missing_field_ids} do not exist in farm {farm_id}.")

        if (
            self.planting_plan_field_relation_repository is not None
            and self.planting_plan_field_relation_repository.list_linked_field_ids(normalized_field_ids)
        ):
            linked_field_ids = self.planting_plan_field_relation_repository.list_linked_field_ids(normalized_field_ids)
            raise ConflictError(f"Fields {linked_field_ids} are referenced by planting plans and cannot be deleted.")

        for field_id in normalized_field_ids:
            relation = self.farm_field_relation_repository.get_by_farm_field(farm_id, field_id)
            field = self.field_repository.get(field_id)
            if relation is None or field is None:
                raise LookupError(f"Field {field_id} does not exist in farm {farm_id}.")
            relation_count = self.farm_field_relation_repository.count_by_field(field_id)
            self.farm_field_relation_repository.delete(relation)
            if relation_count <= 1:
                self.field_repository.delete(field)

    def _get_farm(self, farm_id: int) -> Farm:
        farm = self.farm_repository.get(farm_id)
        if farm is None:
            raise LookupError(f"Farm {farm_id} does not exist.")
        return farm

    def _get_field_in_farm(self, farm_id: int, field_id: int) -> Field:
        self._get_farm(farm_id)
        relation = self.farm_field_relation_repository.get_by_farm_field(farm_id, field_id)
        if relation is None:
            raise LookupError(f"Field {field_id} does not exist in farm {farm_id}.")
        field = self.field_repository.get(field_id)
        if field is None:
            raise LookupError(f"Field {field_id} does not exist.")
        return field

    def _ensure_external_field_id_available(
        self,
        farm_id: int,
        external_field_id: str | None,
        *,
        current_field_id: int | None = None,
    ) -> None:
        if external_field_id is None:
            return
        existing = self._get_field_by_external_field_id_in_farm(farm_id, external_field_id)
        if existing is not None and existing.id != current_field_id:
            raise ValueError(f"external_field_id {external_field_id} already exists.")

    def _get_field_by_external_field_id_in_farm(self, farm_id: int, external_field_id: str) -> Field | None:
        field_ids = self.farm_field_relation_repository.list_field_ids_by_farm(farm_id)
        if not field_ids:
            return None
        fields = self.field_repository.list_by_ids(field_ids)
        return next((field for field in fields if field.external_field_id == external_field_id), None)


class FarmFieldQueryService:
    def __init__(
        self,
        field_repository: FieldRepository,
        farm_repository: FarmRepository,
        farm_field_relation_repository: FarmFieldRelationRepository,
    ) -> None:
        self.field_repository = field_repository
        self.farm_repository = farm_repository
        self.farm_field_relation_repository = farm_field_relation_repository

    def list_by_farm(self, farm_id: int) -> list[Field]:
        self._get_farm(farm_id)
        field_ids = self.farm_field_relation_repository.list_field_ids_by_farm(farm_id)
        return self.field_repository.list_by_ids(field_ids)

    def get(self, farm_id: int, field_id: int) -> Field:
        self._get_farm(farm_id)
        relation = self.farm_field_relation_repository.get_by_farm_field(farm_id, field_id)
        if relation is None:
            raise LookupError(f"Field {field_id} does not exist in farm {farm_id}.")
        field = self.field_repository.get(field_id)
        if field is None:
            raise LookupError(f"Field {field_id} does not exist.")
        return field

    def _get_farm(self, farm_id: int) -> Farm:
        farm = self.farm_repository.get(farm_id)
        if farm is None:
            raise LookupError(f"Farm {farm_id} does not exist.")
        return farm


def _require_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required.")
    return normalized


def _require_required_update_string(value: Any, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} cannot be null.")
    return _require_non_empty(value, field_name)


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _find_duplicate_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value is None:
            continue
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def _validate_latitude(value: Decimal | None, *, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if value < Decimal("-90") or value > Decimal("90"):
        raise ValueError(f"{field_name} must be between -90 and 90.")
    return value


def _validate_longitude(value: Decimal | None, *, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if value < Decimal("-180") or value > Decimal("180"):
        raise ValueError(f"{field_name} must be between -180 and 180.")
    return value


def _validate_area_ha(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    if value <= Decimal("0"):
        raise ValueError("area_ha must be greater than 0.")
    return value
