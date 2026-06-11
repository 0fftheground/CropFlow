# CropFlow Remote DB Bootstrap

本文档用于在“本地通过 SSH tunnel 连远程 PostgreSQL”的场景下，手动完成建表和必要数据初始化。

## 1. 适用范围

适用于：

```text
1. 你当前只能在本地通过 tunnel 访问目标数据库。
2. 你希望先把目标库初始化好，再做 Docker 部署。
3. 你只需要最小必需数据，或按需切换到完整演示数据。
```

默认建议：

```text
1. 生产或准生产初始化，用 reference 模式。
2. 只有内部演示环境，才用 demo 模式。
```

## 2. tunnel 准备

如果你已经在 DBeaver 里配过 SSH，本质上需要把同样的信息转换成一个本地端口转发。

示例：

```powershell
ssh -L 15432:REMOTE_DB_HOST:5432 SSH_USER@SSH_HOST -N
```

示例含义：

```text
1. 远程数据库真实地址是 REMOTE_DB_HOST:5432。
2. 你通过 SSH_HOST 这台跳板机连过去。
3. 本地把它映射成 127.0.0.1:15432。
```

## 3. 连接串准备

把代码连接到本机 tunnel 暴露的端口：

```text
postgresql+psycopg://DB_USER:DB_PASSWORD@127.0.0.1:15432/DB_NAME
```

## 4. 一键执行脚本

仓库已提供脚本：

```text
scripts/bootstrap-db.ps1
```

默认行为：

```text
1. 使用仓库 .venv\Scripts\python.exe
2. 执行 alembic upgrade head
3. 默认执行 scripts/seed_reference_data.py
4. 如显式提供 FarmFieldSourceUrl，再继续导入源库的真实农场 / 地块 / 关联数据
```

### 4.1 初始化最小必要数据

```powershell
powershell -File scripts/bootstrap-db.ps1 `
  -DatabaseUrl "postgresql+psycopg://DB_USER:DB_PASSWORD@127.0.0.1:15432/DB_NAME"
```

会写入：

```text
1. 全部表结构 migration
2. cf_code_dict
3. cf_crop_stage_dict
4. cf_rice_variety
5. pp_rice_control_window_level_1
6. cf_farm
7. cf_field
8. cf_farm_field_relation
```

不会写入：

```text
1. PlantingPlan
2. CalendarItem
3. FarmingTask
4. Execution / Review / Feedback
5. 演示任务链路数据
```

### 4.2 初始化完整演示数据

```powershell
powershell -File scripts/bootstrap-db.ps1 `
  -DatabaseUrl "postgresql+psycopg://DB_USER:DB_PASSWORD@127.0.0.1:15432/DB_NAME" `
  -SeedMode demo
```

### 4.3 在同一个脚本里导入真实农场 / 地块 / 关联数据

如果你认为 `cf_farm`、`cf_field`、`cf_farm_field_relation` 也属于部署时必须带上的基础主数据，可以在 bootstrap 时直接附带导入：

```powershell
powershell -File scripts/bootstrap-db.ps1 `
  -DatabaseUrl "postgresql+psycopg://TGT_USER:TGT_PASSWORD@127.0.0.1:15432/TGT_DB" `
  -FarmFieldSourceUrl "postgresql+psycopg://SRC_USER:SRC_PASSWORD@127.0.0.1:15432/SRC_DB" `
  -ReplaceFarmFieldData
```

行为：

```text
1. 先对目标库执行 migration。
2. 先写基础参考数据。
3. 再读取源库的 cf_farm、cf_field、cf_farm_field_relation。
4. 如带 --ReplaceFarmFieldData，则先删目标库三张表现有数据，再导入真实数据。
```

## 5. 分步执行

如果你不想走一键脚本，也可以手动执行：

```powershell
$env:CROPFLOW_DATABASE_URL="postgresql+psycopg://DB_USER:DB_PASSWORD@127.0.0.1:15432/DB_NAME"
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe scripts/seed_reference_data.py
```

## 6. 可选参数

只迁移，不导数据：

```powershell
powershell -File scripts/bootstrap-db.ps1 `
  -DatabaseUrl "postgresql+psycopg://DB_USER:DB_PASSWORD@127.0.0.1:15432/DB_NAME" `
  -SkipSeed
```

只导数据，不跑 migration：

```powershell
powershell -File scripts/bootstrap-db.ps1 `
  -DatabaseUrl "postgresql+psycopg://DB_USER:DB_PASSWORD@127.0.0.1:15432/DB_NAME" `
  -SkipMigrate
```

## 7. 验证建议

执行完成后，至少确认：

```text
1. alembic 已到 head
2. cf_code_dict 有数据
3. cf_crop_stage_dict 有数据
4. cf_rice_variety 有数据
5. pp_rice_control_window_level_1 有数据
6. cf_farm / cf_field / cf_farm_field_relation 已有默认初始化数据
```

## 8. 后续 Docker 部署

目标库初始化完成后，再去做 Docker 部署：

```text
1. 服务器上配置 .env
2. CROPFLOW_DATABASE_URL 指向正式数据库地址
3. docker compose up -d --build api
4. 如需后台任务，再启动 scheduler
```

## 9. 迁移实际农场 / 地块 / 农场地块数据

如果目标库已经完成 migration，但你还需要把旧库里的真实 `cf_farm`、`cf_field`、`cf_farm_field_relation` 数据迁过去，使用：

```text
scripts/migrate_farm_field_data.py
```

推荐做法：

```text
1. 优先直接在 bootstrap-db.ps1 中通过 FarmFieldSourceUrl 一次做完。
2. 如果目标库已经初始化完，再单独执行这个脚本补迁移。
2. 如果目标库里已经有 reference seed 写入的默认农场/地块，迁移时加 --replace-target。
3. 这样会删掉目标库已有的三张表数据，再导入源库真实数据。
```

示例命令：

```powershell
.venv\Scripts\python.exe scripts/migrate_farm_field_data.py `
  --source-url "postgresql+psycopg://SRC_USER:SRC_PASSWORD@127.0.0.1:15432/SRC_DB" `
  --target-url "postgresql+psycopg://TGT_USER:TGT_PASSWORD@127.0.0.1:15432/TGT_DB" `
  --replace-target
```

行为说明：

```text
1. 读取源库的 cf_farm、cf_field、cf_farm_field_relation。
2. 保留源库主键 id。
3. 将这些记录写入目标库。
4. 自动同步目标库三张表的 id sequence。
```
