from __future__ import annotations

import argparse

from app.bootstrap.table_sync import compare_tables_between_databases, list_supported_table_names


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare configured tables between PostgreSQL databases.",
    )
    parser.add_argument("--source-url", help="Source database URL.")
    parser.add_argument("--target-url", help="Target database URL.")
    parser.add_argument(
        "--tables",
        nargs="+",
        help="Configured table names to compare. Omit to compare the default supported table set.",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=5,
        help="How many sample row ids to print for insert/delete/update differences.",
    )
    parser.add_argument(
        "--list-supported-tables",
        action="store_true",
        help="Print supported table names and exit.",
    )
    args = parser.parse_args()

    if args.list_supported_tables:
        for table_name in list_supported_table_names():
            print(table_name)
        return

    if not args.source_url or not args.target_url:
        parser.error("--source-url and --target-url are required unless --list-supported-tables is used.")

    results = compare_tables_between_databases(
        source_url=args.source_url,
        target_url=args.target_url,
        table_names=args.tables,
        sample_limit=args.sample_limit,
    )

    print("Table diff completed.")
    for result in results:
        print(
            f"{result.table_name}"
            f" source_exists={result.source_table_exists}"
            f" target_exists={result.target_table_exists}"
            f" source_count={result.source_row_count}"
            f" target_count={result.target_row_count}"
            f" missing_in_target={result.missing_in_target_count}"
            f" missing_in_source={result.missing_in_source_count}"
            f" changed_rows={result.changed_row_count}",
        )
        if result.source_missing_columns:
            print(f"  source_missing_columns={list(result.source_missing_columns)}")
        if result.target_missing_columns:
            print(f"  target_missing_columns={list(result.target_missing_columns)}")
        if result.sample_missing_in_target_keys:
            print(f"  sample_missing_in_target={list(result.sample_missing_in_target_keys)}")
        if result.sample_missing_in_source_keys:
            print(f"  sample_missing_in_source={list(result.sample_missing_in_source_keys)}")
        if result.sample_changed_rows:
            sample_updates = [
                {
                    "row_key": item.row_key,
                    "changed_columns": list(item.changed_columns),
                }
                for item in result.sample_changed_rows
            ]
            print(f"  sample_changed_rows={sample_updates}")


if __name__ == "__main__":
    main()
