# CropFlow 本地开发 Runbook

> 本文档用于仓库级的本地开发启动、自检和联调准备。  
> 只放不依赖单个 phase 的稳定本地运行方式。

## 1. 启动前提

需要具备：

1. 本地 PostgreSQL 可连接
2. 已完成 migration
3. 仓库虚拟环境可执行 `.venv\Scripts\python.exe`

数据库配置来源：

```text
1. 优先读取 CROPFLOW_DATABASE_URL
2. 否则读取 database/sql/db_config.json
```

## 2. 启动 API

前台启动：

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

如需热重载，可手动追加 `--reload`。

后台启动并把日志落到项目目录：

```powershell
if (!(Test-Path .codex-temp)) { New-Item -ItemType Directory -Path .codex-temp | Out-Null }
Start-Process `
  -FilePath ".venv\Scripts\python.exe" `
  -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000") `
  -WorkingDirectory "." `
  -RedirectStandardOutput ".codex-temp\cropflow-api.stdout.log" `
  -RedirectStandardError ".codex-temp\cropflow-api.stderr.log" `
  -WindowStyle Hidden
```

健康检查：

```powershell
curl http://127.0.0.1:8000/api/health
```

## 3. 启动 scheduler

```powershell
.venv\Scripts\python.exe -m app.jobs.runner
```

如切换了 `CROPFLOW_*` 环境变量，需要重启 API 或 scheduler。

## 4. 初始化本地数据

如本地库还没建到最新结构，先执行：

```powershell
.venv\Scripts\python.exe -m alembic upgrade head
```

```powershell
.venv\Scripts\python.exe scripts/seed_local_dev_data.py
```

用途：

1. 准备联调所需基础数据
2. 预置示例计划和地块
3. 同步导入 `pp_rice_control_window_level_1.csv`
4. 同步导入 `cf_crop_stage_dict_20260601.csv`

如果只需要最小必需参考数据，不要演示农场 / 计划 / 任务数据，执行：

```powershell
.venv\Scripts\python.exe scripts/seed_reference_data.py
```

用途：

1. 初始化 `cf_code_dict`
2. 初始化 `cf_crop_stage_dict`
3. 初始化 `cf_rice_variety`
4. 初始化 `pp_rice_control_window_level_1`
5. 初始化 `cf_farm`
6. 初始化 `cf_field`
7. 初始化 `cf_farm_field_relation`

## 5. 后端自检

健康检查：

```powershell
curl http://127.0.0.1:8000/api/health
```

全量测试：

```powershell
.venv\Scripts\python.exe -m pytest
```

## 6. 当前环境注意事项

1. 当前项目应优先使用仓库自带虚拟环境 `.venv\Scripts\python.exe`。
2. 不要默认使用系统 `python` 或 `py38` 环境；当前代码已使用 `str | None` 等 `Python 3.10+` 语法，`py38` 会直接启动失败。
3. 如果本地有多个 Conda 环境，不要假设任一全局 `python` 与仓库依赖一致。
4. 本地 API 日志默认可落到：
   `./.codex-temp/cropflow-api.stdout.log`
   `./.codex-temp/cropflow-api.stderr.log`
5. 如果需要通过本地 SSH tunnel 初始化远程数据库，优先看 `docs/development/remote-db-bootstrap.md`，或直接执行 `scripts/bootstrap-db.ps1`。
