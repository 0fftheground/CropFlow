# CropFlow Remote DB Sync

本文档只保留两个高频场景：

```text
1. 本地开发、测试、补数据后，把必要内容同步到远程库。
2. 从远程库拉回数据到本地库，做联调或问题复现。
```

如果你只记一件事，优先用：

```text
scripts/sync-remote-db.ps1
```

它会把这几件事串起来：

```text
1. 对目标库执行 alembic upgrade head
2. 按需执行 reference/demo seed
3. 把显式配置的表从 source 库同步到 target 库
```

现在建议的默认流程不是“先全量覆盖”，而是：

```text
1. 先看 source / target 之间哪些基础表真的有差异
2. 再决定要同步哪些表
3. 最后才执行 sync
```

## 1. 先准备连接串

本地和远程都使用 SQLAlchemy URL：

```text
postgresql+psycopg://DB_USER:DB_PASSWORD@HOST:PORT/DB_NAME
```

如果远程库需要先走 SSH tunnel，先在本地开端口转发：

```powershell
ssh -L 15432:REMOTE_DB_HOST:5432 SSH_USER@SSH_HOST -N
```

然后把远程库连接串写成：

```text
postgresql+psycopg://DB_USER:DB_PASSWORD@127.0.0.1:15432/DB_NAME
```

## 2. 场景 A：把本地库同步到远程库

这是最常见的用法。source 默认取你当前本地 CropFlow 配置里的数据库，target 显式传远程库：

```powershell
powershell -File scripts/sync-remote-db.ps1 `
  -TargetDatabaseUrl "postgresql+psycopg://TGT_USER:TGT_PASSWORD@127.0.0.1:15432/TGT_DB"
```

默认行为：

```text
1. 自动解析当前本地库作为 source
2. 先对远程库跑 migration
3. 默认执行 reference seed
4. 默认把“支持同步的默认表集合”按 merge 模式同步到远程库
```

`merge` 的含义：

```text
1. 不先删目标表现有数据
2. 对 source 中存在的主键执行 insert / update
3. target 中“本地没有但远程已有”的记录默认保留
```

如果你明确需要目标库和 source 完全一致，再显式指定 `exact`。

`exact` 的含义：

```text
1. 先删目标库中选定表的现有数据
2. 再把 source 库中的这些表完整写入 target
3. 目标库会尽量和 source 库保持一致
```

如果你明确要做覆盖同步：

```powershell
powershell -File scripts/sync-remote-db.ps1 `
  -TargetDatabaseUrl "postgresql+psycopg://TGT_USER:TGT_PASSWORD@127.0.0.1:15432/TGT_DB" `
  -TableSyncMode exact
```

## 3. 场景 B：把远程库拉回本地库

这个脚本本身就是双向的，关键只是谁做 source、谁做 target。

如果你希望把远程数据拉回本地测试库：

```powershell
powershell -File scripts/sync-remote-db.ps1 `
  -SourceDatabaseUrl "postgresql+psycopg://REMOTE_USER:REMOTE_PASSWORD@127.0.0.1:15432/REMOTE_DB" `
  -TargetDatabaseUrl "postgresql+psycopg://LOCAL_USER:LOCAL_PASSWORD@127.0.0.1:5432/LOCAL_DB"
```

建议：

```text
1. 拉远程到本地时，优先同步到专门的本地测试库，不要直接覆盖你日常开发库。
2. 如果只是想补某几张主数据表，显式传 -SyncTables，不要无差别全拉。
3. 如果本地已经有自己录入的测试数据，先考虑 merge 模式。
```

如果 target 已经完成基础 seed，只想同步指定表，建议显式加：

```text
-SkipSeed
```

这样可以避免每次都先重跑 reference seed。

## 4. 只同步你指定的表

## 4.0 先看差异，再决定同步哪些表

先做差异预览：

```powershell
.venv\Scripts\python.exe scripts/compare_table_data.py `
  --source-url "postgresql+psycopg://SRC_USER:SRC_PASSWORD@127.0.0.1:5432/SRC_DB" `
  --target-url "postgresql+psycopg://TGT_USER:TGT_PASSWORD@127.0.0.1:15432/TGT_DB"
```

如果只看某几张基础表：

```powershell
.venv\Scripts\python.exe scripts/compare_table_data.py `
  --source-url "postgresql+psycopg://SRC_USER:SRC_PASSWORD@127.0.0.1:5432/SRC_DB" `
  --target-url "postgresql+psycopg://TGT_USER:TGT_PASSWORD@127.0.0.1:15432/TGT_DB" `
  --tables cf_administrative_division cf_farm cf_field cf_farm_field_relation
```

也可以直接通过同步入口先预检、不落库：

```powershell
powershell -File scripts/sync-remote-db.ps1 `
  -TargetDatabaseUrl "postgresql+psycopg://TGT_USER:TGT_PASSWORD@127.0.0.1:15432/TGT_DB" `
  -PreviewTableDiff `
  -StopAfterTableDiff
```

差异输出的含义：

```text
1. missing_in_target：source 有、target 没有，通常表示需要新增到 target
2. missing_in_source：target 有、source 没有，exact 模式下会被删，merge 模式下会保留
3. changed_rows：主键相同，但业务字段内容不同
4. 默认忽略 created_by_* / created_at / updated_at 这类审计字段，只看业务字段变化
5. source_missing_columns / target_missing_columns：表示两边 schema 还没完全对齐，常见于远程库 migration 还没升级
```

如果你最近新建了 `cf_administrative_division` 这类表，或者以后新增任何需要“全量同步”的表，都通过 `-SyncTables` 显式传入：

```powershell
powershell -File scripts/sync-remote-db.ps1 `
  -TargetDatabaseUrl "postgresql+psycopg://TGT_USER:TGT_PASSWORD@127.0.0.1:15432/TGT_DB" `
  -SyncTables cf_administrative_division
```

多个表：

```powershell
powershell -File scripts/sync-remote-db.ps1 `
  -TargetDatabaseUrl "postgresql+psycopg://TGT_USER:TGT_PASSWORD@127.0.0.1:15432/TGT_DB" `
  -SyncTables cf_administrative_division,cf_farm,cf_field,cf_farm_field_relation
```

查看当前脚本已经支持哪些表：

```powershell
.venv\Scripts\python.exe scripts/sync_table_data.py --list-supported-tables
```

## 5. 以后新增表，要改哪里

同步表是显式白名单，不会自动扫描全库。

要让一个新表进入同步流程，改这里：

```text
app/bootstrap/table_sync.py
```

需要做两件事：

```text
1. 在 SUPPORTED_TABLES 里补一条 TableSyncConfig，声明表名、字段列表和同步顺序。
2. 如果你希望它成为默认同步集合，再把表名加入 DEFAULT_SYNC_TABLES。
```

当前默认支持表：

```text
cf_administrative_division
cf_code_dict
cf_crop_stage_dict
cf_rice_variety
pp_rice_control_window_level_1
cf_farm
cf_field
cf_farm_field_relation
```

## 6. 低层脚本分别做什么

一般只需要记住 `sync-remote-db.ps1`。下面这些脚本只在你要拆步骤时再单独用：

```text
scripts/bootstrap-db.ps1
  只负责 target 库 migration + seed

scripts/sync_table_data.py
  只负责表数据同步，不管 migration

scripts/migrate_farm_field_data.py
  只是 cf_farm / cf_field / cf_farm_field_relation 的专用兼容入口
```

## 7. 推荐命令模板

先只看差异，不落库：

```powershell
powershell -File scripts/sync-remote-db.ps1 `
  -TargetDatabaseUrl "postgresql+psycopg://TGT_USER:TGT_PASSWORD@127.0.0.1:15432/TGT_DB" `
  -PreviewTableDiff `
  -StopAfterTableDiff
```

推本地到远程：

```powershell
powershell -File scripts/sync-remote-db.ps1 `
  -TargetDatabaseUrl "postgresql+psycopg://TGT_USER:TGT_PASSWORD@127.0.0.1:15432/TGT_DB"
```

推本地到远程，但只同步指定表：

```powershell
powershell -File scripts/sync-remote-db.ps1 `
  -TargetDatabaseUrl "postgresql+psycopg://TGT_USER:TGT_PASSWORD@127.0.0.1:15432/TGT_DB" `
  -SyncTables cf_administrative_division
```

推本地到远程，并显式要求 exact 覆盖：

```powershell
powershell -File scripts/sync-remote-db.ps1 `
  -TargetDatabaseUrl "postgresql+psycopg://TGT_USER:TGT_PASSWORD@127.0.0.1:15432/TGT_DB" `
  -SyncTables cf_administrative_division,cf_farm,cf_field,cf_farm_field_relation `
  -TableSyncMode exact
```

拉远程到本地：

```powershell
powershell -File scripts/sync-remote-db.ps1 `
  -SourceDatabaseUrl "postgresql+psycopg://REMOTE_USER:REMOTE_PASSWORD@127.0.0.1:15432/REMOTE_DB" `
  -TargetDatabaseUrl "postgresql+psycopg://LOCAL_USER:LOCAL_PASSWORD@127.0.0.1:5432/LOCAL_DB"
```

拉远程到本地，但保留本地已有数据做 merge：

```powershell
powershell -File scripts/sync-remote-db.ps1 `
  -SourceDatabaseUrl "postgresql+psycopg://REMOTE_USER:REMOTE_PASSWORD@127.0.0.1:15432/REMOTE_DB" `
  -TargetDatabaseUrl "postgresql+psycopg://LOCAL_USER:LOCAL_PASSWORD@127.0.0.1:5432/LOCAL_DB" `
  -TableSyncMode merge
```

## 8. 验证状态

`2026-06-25` 已对以下命令做过真实 PostgreSQL 实测：

```text
1. scripts/sync_table_data.py --list-supported-tables
2. sync-remote-db.ps1：本地 source -> 临时 target，exact 模式，SyncTables=cf_administrative_division
3. sync-remote-db.ps1：临时 source -> 临时 target，exact 模式，模拟“远程拉本地”
4. sync-remote-db.ps1：本地 source -> 临时 target，merge 模式，SyncTables=cf_administrative_division
5. sync-remote-db.ps1：本地 source -> 远程 tunnel target，exact 模式，SyncTables=cf_administrative_division，SkipSeed
6. sync-remote-db.ps1：远程 tunnel source -> 本地 target，exact 模式，SyncTables=cf_administrative_division，SkipSeed
7. compare_table_data.py：本地 source vs 远程 tunnel target，差异预览，支持只看指定表和样例 row id
```

说明：

```text
1. 上述验证使用真实本地 PostgreSQL 临时数据库，不是 mock。
2. 其中第 5 和第 6 项已通过真实 SSH tunnel 远程实例验证。
3. 当前文档中的 URL 占位符只需要替换成实际 source/target 连接串即可。
4. fresh target + 默认 seed 在 tunnel 场景下目前可能非常慢，因为 `seed_reference_data.py` 对行政区划是逐条 `session.get()`；如果目标库已经初始化过，优先用 `-SkipSeed`。
```
