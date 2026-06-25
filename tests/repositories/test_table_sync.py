from __future__ import annotations

import pytest

from app.bootstrap.table_sync import (
    DEFAULT_SYNC_TABLES,
    TableRowDiffSample,
    SUPPORTED_TABLES,
    _build_table_diff_result,
    list_supported_table_names,
    resolve_table_configs,
)


def test_list_supported_table_names_matches_default_order() -> None:
    assert list_supported_table_names() == list(DEFAULT_SYNC_TABLES)


def test_resolve_table_configs_returns_default_order_when_omitted() -> None:
    configs = resolve_table_configs(None)

    assert [item.table_name for item in configs] == list(DEFAULT_SYNC_TABLES)


def test_resolve_table_configs_dedupes_and_sorts_by_sync_order() -> None:
    configs = resolve_table_configs(
        [
            "cf_field",
            "cf_administrative_division",
            "cf_field",
            "cf_farm",
        ],
    )

    assert [item.table_name for item in configs] == [
        "cf_administrative_division",
        "cf_farm",
        "cf_field",
    ]


def test_resolve_table_configs_supports_comma_separated_names() -> None:
    configs = resolve_table_configs(
        [
            "cf_administrative_division,cf_farm",
            "cf_field",
        ],
    )

    assert [item.table_name for item in configs] == [
        "cf_administrative_division",
        "cf_farm",
        "cf_field",
    ]


def test_resolve_table_configs_rejects_unsupported_tables() -> None:
    with pytest.raises(ValueError, match="Unsupported sync tables"):
        resolve_table_configs(["cf_unknown_table"])


def test_build_table_diff_result_ignores_audit_only_changes() -> None:
    config = SUPPORTED_TABLES["cf_code_dict"]
    result = _build_table_diff_result(
        config=config,
        source_table_exists=True,
        target_table_exists=True,
        source_missing_columns=(),
        target_missing_columns=(),
        source_rows={
            1: {
                "id": 1,
                "code": 1001,
                "code_name": "播种",
                "category": "task",
                "is_active": True,
                "created_by_type": "system",
                "created_by_id": "seed",
                "created_at": "2026-06-01 00:00:00",
                "updated_at": "2026-06-01 00:00:00",
            },
        },
        target_rows={
            1: {
                "id": 1,
                "code": 1001,
                "code_name": "播种",
                "category": "task",
                "is_active": True,
                "created_by_type": "manual",
                "created_by_id": "alice",
                "created_at": "2026-06-02 00:00:00",
                "updated_at": "2026-06-02 00:00:00",
            },
        },
        sample_limit=5,
    )

    assert result.changed_row_count == 0
    assert result.sample_changed_rows == ()


def test_build_table_diff_result_reports_insert_delete_and_update_samples() -> None:
    config = SUPPORTED_TABLES["cf_farm"]
    result = _build_table_diff_result(
        config=config,
        source_table_exists=True,
        target_table_exists=True,
        source_missing_columns=(),
        target_missing_columns=(),
        source_rows={
            1: {
                "id": 1,
                "farm_name": "Alpha",
                "external_farm_id": "A-1",
                "province": "湖南省",
                "city": "益阳市",
                "district_county": "桃江县",
                "adcode": "430922",
                "boundary_wkt": None,
                "centroid_lat": None,
                "centroid_lon": None,
                "created_by_type": "system",
                "created_by_id": "seed",
                "created_at": "2026-06-01 00:00:00",
                "updated_at": "2026-06-01 00:00:00",
            },
            2: {
                "id": 2,
                "farm_name": "Beta",
                "external_farm_id": "B-1",
                "province": "湖南省",
                "city": "长沙市",
                "district_county": "岳麓区",
                "adcode": "430104",
                "boundary_wkt": None,
                "centroid_lat": None,
                "centroid_lon": None,
                "created_by_type": "system",
                "created_by_id": "seed",
                "created_at": "2026-06-01 00:00:00",
                "updated_at": "2026-06-01 00:00:00",
            },
        },
        target_rows={
            1: {
                "id": 1,
                "farm_name": "Alpha Updated",
                "external_farm_id": "A-1",
                "province": "湖南省",
                "city": "益阳市",
                "district_county": "桃江县",
                "adcode": "430922",
                "boundary_wkt": None,
                "centroid_lat": None,
                "centroid_lon": None,
                "created_by_type": "manual",
                "created_by_id": "alice",
                "created_at": "2026-06-02 00:00:00",
                "updated_at": "2026-06-02 00:00:00",
            },
            3: {
                "id": 3,
                "farm_name": "Gamma",
                "external_farm_id": "G-1",
                "province": "湖南省",
                "city": "株洲市",
                "district_county": "天元区",
                "adcode": "430211",
                "boundary_wkt": None,
                "centroid_lat": None,
                "centroid_lon": None,
                "created_by_type": "system",
                "created_by_id": "seed",
                "created_at": "2026-06-01 00:00:00",
                "updated_at": "2026-06-01 00:00:00",
            },
        },
        sample_limit=5,
    )

    assert result.missing_in_target_count == 1
    assert result.sample_missing_in_target_keys == (2,)
    assert result.missing_in_source_count == 1
    assert result.sample_missing_in_source_keys == (3,)
    assert result.changed_row_count == 1
    assert result.sample_changed_rows == (
        TableRowDiffSample(row_key=1, changed_columns=("farm_name",)),
    )
