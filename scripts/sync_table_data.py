from __future__ import annotations

import argparse

from app.bootstrap.table_sync import list_supported_table_names, sync_tables_between_databases


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync configured tables between PostgreSQL databases.",
    )
    parser.add_argument("--source-url", help="Source database URL.")
    parser.add_argument("--target-url", help="Target database URL.")
    parser.add_argument(
        "--tables",
        nargs="+",
        help="Configured table names to sync. Omit to sync the default supported table set.",
    )
    parser.add_argument(
        "--replace-target",
        action="store_true",
        help="Delete target rows for the selected tables before import.",
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

    results = sync_tables_between_databases(
        source_url=args.source_url,
        target_url=args.target_url,
        table_names=args.tables,
        replace_target=args.replace_target,
    )

    print("Table sync completed.")
    for result in results:
        print(f"{result.table_name}={result.row_count}")


if __name__ == "__main__":
    main()
