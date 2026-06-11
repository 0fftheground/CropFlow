from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.sql import quoted_name

FARM_COLUMNS = [
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
]

FIELD_COLUMNS = [
    "id",
    "field_name",
    "boundary_wkt",
    "centroid_lat",
    "centroid_lon",
    "area_ha",
    "created_by_type",
    "created_by_id",
    "created_at",
    "updated_at",
]

RELATION_COLUMNS = [
    "id",
    "farm_id",
    "field_id",
    "created_by_type",
    "created_by_id",
    "created_at",
    "updated_at",
]


@dataclass(slots=True)
class MigrationSummary:
    farm_count: int
    field_count: int
    relation_count: int


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate cf_farm / cf_field / cf_farm_field_relation data between PostgreSQL databases.",
    )
    parser.add_argument("--source-url", required=True, help="Source database URL.")
    parser.add_argument("--target-url", required=True, help="Target database URL.")
    parser.add_argument(
        "--replace-target",
        action="store_true",
        help="Delete target cf_farm_field_relation / cf_field / cf_farm data before import.",
    )
    args = parser.parse_args()

    source_engine = create_engine(args.source_url, pool_pre_ping=True)
    target_engine = create_engine(args.target_url, pool_pre_ping=True)

    with source_engine.connect() as source_conn:
        farms = _fetch_rows(source_conn, "cf_farm", FARM_COLUMNS)
        fields = _fetch_rows(source_conn, "cf_field", FIELD_COLUMNS)
        relations = _fetch_rows(source_conn, "cf_farm_field_relation", RELATION_COLUMNS)

    with target_engine.begin() as target_conn:
        if args.replace_target:
            _clear_target_tables(target_conn)

        _upsert_rows(target_conn, "cf_farm", FARM_COLUMNS, farms, conflict_target="id")
        _upsert_rows(target_conn, "cf_field", FIELD_COLUMNS, fields, conflict_target="id")
        _upsert_rows(
            target_conn,
            "cf_farm_field_relation",
            RELATION_COLUMNS,
            relations,
            conflict_target="id",
        )

        _sync_id_sequence(target_conn, "cf_farm")
        _sync_id_sequence(target_conn, "cf_field")
        _sync_id_sequence(target_conn, "cf_farm_field_relation")

    summary = MigrationSummary(
        farm_count=len(farms),
        field_count=len(fields),
        relation_count=len(relations),
    )
    print("Farm/field migration completed.")
    print(f"farm_count={summary.farm_count}")
    print(f"field_count={summary.field_count}")
    print(f"relation_count={summary.relation_count}")


def _fetch_rows(conn: Connection, table_name: str, columns: list[str]) -> list[dict]:
    order_by = "id"
    stmt = text(
        f"SELECT {', '.join(columns)} FROM {table_name} ORDER BY {order_by}",
    )
    return [dict(row._mapping) for row in conn.execute(stmt)]


def _clear_target_tables(conn: Connection) -> None:
    conn.execute(text("DELETE FROM cf_farm_field_relation"))
    conn.execute(text("DELETE FROM cf_field"))
    conn.execute(text("DELETE FROM cf_farm"))


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
                COALESCE((SELECT MAX(id) FROM {safe_table_name}), 1),
                true
            )
            """,
        ),
    )


if __name__ == "__main__":
    main()
