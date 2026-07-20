from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.models import AdministrativeDivision
from app.services.administrative_divisions import AdministrativeDivisionQueryService


def _make_division(
    *,
    division_id: int,
    code: str,
    name: str,
    division_type: str,
    level: int,
    parent_code: str | None,
    sort_order: int,
) -> AdministrativeDivision:
    return AdministrativeDivision(
        id=division_id,
        code=code,
        adcode=code[:6],
        name=name,
        division_type=division_type,
        level=level,
        parent_code=parent_code,
        sort_order=sort_order,
    )


@dataclass
class FakeAdministrativeDivisionRepository:
    rows: list[AdministrativeDivision]

    def get_by_code_and_level(self, code: str, level: int) -> AdministrativeDivision | None:
        return next((item for item in self.rows if item.code == code and item.level == level), None)

    def list_roots(self) -> list[AdministrativeDivision]:
        return [item for item in self.rows if item.parent_code is None]

    def list_by_parent_code(self, parent_code: str) -> list[AdministrativeDivision]:
        return [item for item in self.rows if item.parent_code == parent_code]

    def has_children(self, code: str) -> bool:
        return any(item.parent_code == code for item in self.rows)


def _build_service() -> AdministrativeDivisionQueryService:
    rows = [
        _make_division(
            division_id=1,
            code="110000000000",
            name="北京市",
            division_type="直辖市",
            level=1,
            parent_code=None,
            sort_order=1,
        ),
        _make_division(
            division_id=2,
            code="110101000000",
            name="东城区",
            division_type="市辖区",
            level=3,
            parent_code="110000000000",
            sort_order=2,
        ),
        _make_division(
            division_id=3,
            code="110102000000",
            name="西城区",
            division_type="市辖区",
            level=3,
            parent_code="110000000000",
            sort_order=3,
        ),
        _make_division(
            division_id=4,
            code="430000000000",
            name="湖南省",
            division_type="省",
            level=1,
            parent_code=None,
            sort_order=4,
        ),
        _make_division(
            division_id=5,
            code="430100000000",
            name="长沙市",
            division_type="地级市",
            level=2,
            parent_code="430000000000",
            sort_order=5,
        ),
        _make_division(
            division_id=6,
            code="430700000000",
            name="常德市",
            division_type="地级市",
            level=2,
            parent_code="430000000000",
            sort_order=6,
        ),
        _make_division(
            division_id=7,
            code="430102000000",
            name="芙蓉区",
            division_type="市辖区",
            level=3,
            parent_code="430100000000",
            sort_order=7,
        ),
    ]
    return AdministrativeDivisionQueryService(
        administrative_division_repository=FakeAdministrativeDivisionRepository(rows),
    )


def test_list_root_nodes_returns_provinces() -> None:
    service = _build_service()

    result = service.list_children()

    assert [item.name for item in result] == ["北京市", "湖南省"]


def test_list_children_returns_prefecture_level_cities_for_regular_province() -> None:
    service = _build_service()

    result = service.list_children("430000000000", parent_level=1)

    assert [item.name for item in result] == ["长沙市", "常德市"]
    assert all(item.level == 2 for item in result)
    assert all(item.is_virtual is False for item in result)


def test_list_children_returns_virtual_city_for_direct_municipality() -> None:
    service = _build_service()

    result = service.list_children("110000000000", parent_level=1)

    assert len(result) == 1
    assert result[0].name == "北京市"
    assert result[0].level == 2
    assert result[0].is_virtual is True
    assert result[0].parent_code == "110000000000"


def test_list_children_returns_districts_for_virtual_direct_municipality_city() -> None:
    service = _build_service()

    result = service.list_children("110000000000", parent_level=2)

    assert [item.name for item in result] == ["东城区", "西城区"]
    assert all(item.level == 3 for item in result)


def test_list_children_requires_parent_level_when_parent_code_is_provided() -> None:
    service = _build_service()

    with pytest.raises(ValueError, match="parent_level is required"):
        service.list_children("430000000000")
