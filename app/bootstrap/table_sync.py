from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.sql import quoted_name


@dataclass(frozen=True, slots=True)
class TableSyncConfig:
    table_name: str
    columns: tuple[str, ...]
    sync_order: int
    clear_order: int
    conflict_target: str = "id"
    reset_sequence: bool = True


@dataclass(frozen=True, slots=True)
class TableSyncResult:
    table_name: str
    row_count: int


@dataclass(frozen=True, slots=True)
class TableRowDiffSample:
    row_key: Any
    changed_columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TableDiffResult:
    table_name: str
    source_table_exists: bool
    target_table_exists: bool
    source_missing_columns: tuple[str, ...]
    target_missing_columns: tuple[str, ...]
    source_row_count: int
    target_row_count: int
    missing_in_target_count: int
    missing_in_source_count: int
    changed_row_count: int
    sample_missing_in_target_keys: tuple[Any, ...]
    sample_missing_in_source_keys: tuple[Any, ...]
    sample_changed_rows: tuple[TableRowDiffSample, ...]


SUPPORTED_TABLES: dict[str, TableSyncConfig] = {
    "cf_administrative_division": TableSyncConfig(
        table_name="cf_administrative_division",
        columns=(
            "id",
            "code",
            "adcode",
            "name",
            "division_type",
            "level",
            "parent_code",
            "sort_order",
            "created_by_type",
            "created_by_id",
            "created_at",
            "updated_at",
        ),
        sync_order=10,
        clear_order=80,
    ),
    "cf_code_dict": TableSyncConfig(
        table_name="cf_code_dict",
        columns=(
            "id",
            "code",
            "code_name",
            "category",
            "is_active",
            "created_by_type",
            "created_by_id",
            "created_at",
            "updated_at",
        ),
        sync_order=20,
        clear_order=70,
    ),
    "cf_crop_stage_dict": TableSyncConfig(
        table_name="cf_crop_stage_dict",
        columns=(
            "id",
            "stage_code",
            "stage_name",
            "season_scope",
            "business_stage_code",
            "display_order",
            "is_active",
            "created_by_type",
            "created_by_id",
            "created_at",
            "updated_at",
        ),
        sync_order=30,
        clear_order=60,
    ),
    "cf_rice_variety": TableSyncConfig(
        table_name="cf_rice_variety",
        columns=(
            "id",
            "name",
            "approve_year",
            "approve_no",
            "approve_region",
            "suitable_region",
            "culti_type_code",
            "sub_type_code",
            "maturity_code",
            "control_variety",
            "growth_days",
            "compare_days",
            "rice_code",
            "created_by_type",
            "created_by_id",
            "created_at",
            "updated_at",
        ),
        sync_order=40,
        clear_order=50,
    ),
    "pp_rice_control_window_level_1": TableSyncConfig(
        table_name="pp_rice_control_window_level_1",
        columns=(
            "id",
            "province",
            "city",
            "county",
            "data_year",
            "detail",
            "created_at",
            "updated_at",
        ),
        sync_order=50,
        clear_order=40,
    ),
    "cf_farm": TableSyncConfig(
        table_name="cf_farm",
        columns=(
            "id",
            "farm_name",
            "external_farm_id",
            "province",
            "city",
            "district_county",
            "adcode",
            "boundary_wkt",
            "centroid_lat",
            "centroid_lon",
            "created_by_type",
            "created_by_id",
            "created_at",
            "updated_at",
        ),
        sync_order=60,
        clear_order=30,
    ),
    "cf_field": TableSyncConfig(
        table_name="cf_field",
        columns=(
            "id",
            "field_name",
            "external_field_id",
            "boundary_wkt",
            "centroid_lat",
            "centroid_lon",
            "area_ha",
            "created_by_type",
            "created_by_id",
            "created_at",
            "updated_at",
        ),
        sync_order=70,
        clear_order=20,
    ),
    "cf_farm_field_relation": TableSyncConfig(
        table_name="cf_farm_field_relation",
        columns=(
            "id",
            "farm_id",
            "field_id",
            "created_by_type",
            "created_by_id",
            "created_at",
            "updated_at",
        ),
        sync_order=80,
        clear_order=10,
    ),
}

DEFAULT_SYNC_TABLES: tuple[str, ...] = (
    "cf_administrative_division",
    "cf_code_dict",
    "cf_crop_stage_dict",
    "cf_rice_variety",
    "pp_rice_control_window_level_1",
    "cf_farm",
    "cf_field",
    "cf_farm_field_relation",
)

AUDIT_COMPARE_EXCLUDED_COLUMNS: tuple[str, ...] = (
    "created_by_type",
    "created_by_id",
    "created_at",
    "updated_at",
)


def list_supported_table_names() -> list[str]:
    return list(DEFAULT_SYNC_TABLES)


def resolve_table_configs(table_names: list[str] | None) -> list[TableSyncConfig]:
    selected_names = table_names or list(DEFAULT_SYNC_TABLES)
    normalized_names = [
        name
        for item in selected_names
        for name in _split_table_names(item)
        if name
    ]

    seen: set[str] = set()
    deduped_names: list[str] = []
    for name in normalized_names:
        if name in seen:
            continue
        seen.add(name)
        deduped_names.append(name)

    unsupported_names = [name for name in deduped_names if name not in SUPPORTED_TABLES]
    if unsupported_names:
        raise ValueError(
            "Unsupported sync tables: "
            + ", ".join(sorted(unsupported_names))
            + ". Supported tables: "
            + ", ".join(list_supported_table_names())
        )

    configs = [SUPPORTED_TABLES[name] for name in deduped_names]
    return sorted(configs, key=lambda item: item.sync_order)


def sync_tables_between_databases(
    *,
    source_url: str,
    target_url: str,
    table_names: list[str] | None = None,
    replace_target: bool = False,
) -> list[TableSyncResult]:
    configs = resolve_table_configs(table_names)
    source_engine = create_engine(source_url, pool_pre_ping=True)
    target_engine = create_engine(target_url, pool_pre_ping=True)

    with source_engine.connect() as source_conn:
        rows_by_table = {
            config.table_name: _fetch_rows(source_conn, config.table_name, list(config.columns))
            for config in configs
        }

    with target_engine.begin() as target_conn:
        if replace_target:
            _clear_target_tables(target_conn, configs)

        for config in configs:
            rows = rows_by_table[config.table_name]
            _upsert_rows(
                target_conn,
                config.table_name,
                list(config.columns),
                rows,
                conflict_target=config.conflict_target,
            )
            if config.reset_sequence:
                _sync_id_sequence(target_conn, config.table_name)

    return [
        TableSyncResult(table_name=config.table_name, row_count=len(rows_by_table[config.table_name]))
        for config in configs
    ]


def compare_tables_between_databases(
    *,
    source_url: str,
    target_url: str,
    table_names: list[str] | None = None,
    sample_limit: int = 5,
) -> list[TableDiffResult]:
    configs = resolve_table_configs(table_names)
    source_engine = create_engine(source_url, pool_pre_ping=True)
    target_engine = create_engine(target_url, pool_pre_ping=True)

    results: list[TableDiffResult] = []
    with source_engine.connect() as source_conn, target_engine.connect() as target_conn:
        for config in configs:
            source_exists = _table_exists(source_conn, config.table_name)
            target_exists = _table_exists(target_conn, config.table_name)
            source_rows, source_missing_columns = _fetch_rows_by_key(
                source_conn,
                config.table_name,
                list(config.columns),
                key_column=config.conflict_target,
                allow_missing=True,
            )
            target_rows, target_missing_columns = _fetch_rows_by_key(
                target_conn,
                config.table_name,
                list(config.columns),
                key_column=config.conflict_target,
                allow_missing=True,
            )
            results.append(
                _build_table_diff_result(
                    config=config,
                    source_table_exists=source_exists,
                    target_table_exists=target_exists,
                    source_missing_columns=source_missing_columns,
                    target_missing_columns=target_missing_columns,
                    source_rows=source_rows,
                    target_rows=target_rows,
                    sample_limit=sample_limit,
                ),
            )

    return results


def _normalize_table_name(value: str | None) -> str:
    return (value or "").strip()


def _split_table_names(value: str | None) -> list[str]:
    normalized = _normalize_table_name(value)
    if not normalized:
        return []
    return [_normalize_table_name(item) for item in normalized.split(",") if _normalize_table_name(item)]


def _fetch_rows(conn: Connection, table_name: str, columns: list[str]) -> list[dict]:
    stmt = text(f"SELECT {', '.join(columns)} FROM {table_name} ORDER BY id")
    return [dict(row._mapping) for row in conn.execute(stmt)]


def _table_exists(conn: Connection, table_name: str) -> bool:
    stmt = text("SELECT to_regclass(:table_name) IS NOT NULL")
    return bool(conn.execute(stmt, {"table_name": f"public.{table_name}"}).scalar_one())


def _fetch_rows_by_key(
    conn: Connection,
    table_name: str,
    columns: list[str],
    *,
    key_column: str,
    allow_missing: bool = False,
) -> tuple[dict[Any, dict[str, Any]], tuple[str, ...]]:
    if not _table_exists(conn, table_name):
        if allow_missing:
            return {}, tuple(columns)
        raise ValueError(f"Table does not exist: {table_name}")

    existing_columns = _get_existing_columns(conn, table_name)
    selected_columns = [column for column in columns if column in existing_columns]
    missing_columns = tuple(column for column in columns if column not in existing_columns)
    if key_column not in selected_columns:
        raise ValueError(f"Key column does not exist on table {table_name}: {key_column}")

    rows = _fetch_rows(conn, table_name, selected_columns)
    normalized_rows = []
    for row in rows:
        normalized_row = {column: row.get(column) for column in selected_columns}
        for column in missing_columns:
            normalized_row[column] = None
        normalized_rows.append(normalized_row)

    return {row[key_column]: row for row in normalized_rows}, missing_columns


def _get_existing_columns(conn: Connection, table_name: str) -> set[str]:
    stmt = text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = :table_name
        """,
    )
    return {str(row[0]) for row in conn.execute(stmt, {"table_name": table_name})}


def _clear_target_tables(conn: Connection, configs: list[TableSyncConfig]) -> None:
    for config in sorted(configs, key=lambda item: item.clear_order):
        conn.execute(text(f"DELETE FROM {config.table_name}"))


def _upsert_rows(
    conn: Connection,
    table_name: str,
    columns: list[str],
    rows: list[dict],
    *,
    conflict_target: str,
) -> None:
    if not rows:
        return

    insert_columns = ", ".join(columns)
    value_placeholders = ", ".join(f":{column}" for column in columns)
    update_assignments = ", ".join(
        f"{column} = EXCLUDED.{column}"
        for column in columns
        if column != conflict_target
    )
    stmt = text(
        f"""
        INSERT INTO {table_name} ({insert_columns})
        VALUES ({value_placeholders})
        ON CONFLICT ({conflict_target}) DO UPDATE
        SET {update_assignments}
        """,
    )
    conn.execute(stmt, rows)


def _sync_id_sequence(conn: Connection, table_name: str) -> None:
    safe_table_name = quoted_name(table_name, quote=False)
    conn.execute(
        text(
            f"""
            SELECT setval(
                pg_get_serial_sequence('{safe_table_name}', 'id'),
                COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                true
            )
            """,
        ),
    )


def _build_table_diff_result(
    *,
    config: TableSyncConfig,
    source_table_exists: bool,
    target_table_exists: bool,
    source_missing_columns: tuple[str, ...],
    target_missing_columns: tuple[str, ...],
    source_rows: dict[Any, dict[str, Any]],
    target_rows: dict[Any, dict[str, Any]],
    sample_limit: int,
) -> TableDiffResult:
    source_keys = set(source_rows.keys())
    target_keys = set(target_rows.keys())

    missing_in_target_keys = sorted(source_keys - target_keys)
    missing_in_source_keys = sorted(target_keys - source_keys)
    compare_columns = _get_compare_columns(config)

    changed_samples: list[TableRowDiffSample] = []
    changed_count = 0
    for row_key in sorted(source_keys & target_keys):
        changed_columns = tuple(
            column
            for column in compare_columns
            if source_rows[row_key].get(column) != target_rows[row_key].get(column)
        )
        if not changed_columns:
            continue
        changed_count += 1
        if len(changed_samples) < sample_limit:
            changed_samples.append(
                TableRowDiffSample(
                    row_key=row_key,
                    changed_columns=changed_columns,
                ),
            )

    return TableDiffResult(
        table_name=config.table_name,
        source_table_exists=source_table_exists,
        target_table_exists=target_table_exists,
        source_missing_columns=source_missing_columns,
        target_missing_columns=target_missing_columns,
        source_row_count=len(source_rows),
        target_row_count=len(target_rows),
        missing_in_target_count=len(missing_in_target_keys),
        missing_in_source_count=len(missing_in_source_keys),
        changed_row_count=changed_count,
        sample_missing_in_target_keys=tuple(missing_in_target_keys[:sample_limit]),
        sample_missing_in_source_keys=tuple(missing_in_source_keys[:sample_limit]),
        sample_changed_rows=tuple(changed_samples),
    )


def _get_compare_columns(config: TableSyncConfig) -> tuple[str, ...]:
    return tuple(
        column
        for column in config.columns
        if column != config.conflict_target and column not in AUDIT_COMPARE_EXCLUDED_COLUMNS
    )
