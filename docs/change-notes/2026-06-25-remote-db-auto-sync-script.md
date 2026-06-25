# 2026-06-25 Remote DB Auto Sync Script

## Summary

新增远程数据库一键同步脚本和通用表同步器，把“当前本地代码对应的最新 schema + 关键 reference seed + 本地显式选定表数据”一次性同步到目标库，减少手工拼接 bootstrap 和数据迁移命令。

## Code Changes

- 新增 `scripts/sync-remote-db.ps1`
- 新增 `scripts/sync_table_data.py`
- 新增 `app/bootstrap/table_sync.py`，集中维护支持同步的表、列和顺序
- `scripts/migrate_farm_field_data.py` 补齐 `cf_field.external_field_id` 同步
- `scripts/seed_reference_data.py` 增加 `administrative_division_count` 输出，方便同步后核对

## Business Logic Changes

- 远程库同步现在有统一入口，不再要求手工先跑 migration、再 seed、再拼数据迁移命令
- 支持通过 `-SyncTables` 显式指定要全量同步的表
- 默认按 merge 模式同步当前支持的默认表集合；只有显式传 `-TableSyncMode exact` 才做覆盖同步
- 当前 reference 数据继续使用仓库本地 seed 文件作为事实源；显式表同步使用本地数据库作为事实源

## Affected Areas

- `scripts/sync-remote-db.ps1`
- `scripts/sync_table_data.py`
- `app/bootstrap/table_sync.py`
- `scripts/migrate_farm_field_data.py`
- `scripts/seed_reference_data.py`
- `docs/development/remote-db-bootstrap.md`

## Tests

建议至少执行：

```text
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync-remote-db.ps1 -TargetDatabaseUrl "postgresql+psycopg://dummy:dummy@127.0.0.1:15432/dummy" -SkipMigrate -SkipSeed -SkipTableSync
.venv\Scripts\python.exe scripts/migrate_farm_field_data.py --help
.venv\Scripts\python.exe scripts/sync_table_data.py --list-supported-tables
```

## Remaining Assumptions

- 当前一键同步脚本覆盖的是数据库 schema、reference seed 和农场/地块基础主数据，不包含应用代码上传、服务器 git pull 或 docker compose 重启。
- reference seed 仍按 upsert 方式写入目标库，不主动清理目标库中已不存在于 seed 文件的旧参考记录。
- 当前“显式可配置同步”的前提是先把表和列加入 `app/bootstrap/table_sync.py` 支持清单；不是对任意未知表名无约束直通。
