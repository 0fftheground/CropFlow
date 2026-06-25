from __future__ import annotations

import argparse

from app.bootstrap.table_sync import sync_tables_between_databases


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

    results = sync_tables_between_databases(
        source_url=args.source_url,
        target_url=args.target_url,
        table_names=["cf_farm", "cf_field", "cf_farm_field_relation"],
        replace_target=args.replace_target,
    )
    result_map = {item.table_name: item.row_count for item in results}

    print("Farm/field migration completed.")
    print(f"farm_count={result_map['cf_farm']}")
    print(f"field_count={result_map['cf_field']}")
    print(f"relation_count={result_map['cf_farm_field_relation']}")


if __name__ == "__main__":
    main()
