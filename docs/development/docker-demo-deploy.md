# CropFlow Docker Demo Deploy

本文档用于在 Linux 服务器上用 Docker Compose 启动一套内部演示环境，也覆盖“应用容器接外部 PostgreSQL”的部署方式。

## 1. 适用范围

这套容器化文件支持两种模式：

```text
1. 内部演示环境：compose 自带 PostgreSQL
2. 外部数据库部署：API / scheduler 连接指定 PostgreSQL 地址
3. 单机 Linux 服务器
4. 默认要求接真实算法和真实天气接口
```

当前仓库的容器化入口文件：

```text
Dockerfile
docker-compose.yml
docker/entrypoint.sh
.env.docker.example
```

## 2. 启动前提

服务器需要具备：

```text
1. Docker Engine
2. Docker Compose Plugin
3. 可访问仓库代码
```

## 3. 环境变量准备

先复制模板：

```bash
cp .env.docker.example .env
```

如果使用 compose 自带数据库，可先保持默认值。

如果使用外部 PostgreSQL：

```text
1. 直接把 CROPFLOW_DATABASE_URL 改成目标库连接串。
2. 不需要启动 compose 里的 db 服务。
3. API / scheduler / seed 容器会直接等待 CROPFLOW_DATABASE_URL 对应的数据库可连接。
```

说明：

```text
1. 默认数据库容器名是 db。
2. 默认数据库名 / 用户 / 密码都是 demo 用配置。
3. API 和 scheduler 默认启用 CROPFLOW_REQUIRE_REAL_INTEGRATIONS=true。
4. 如果缺少真实接口地址或天气 token，容器会在启动时直接失败，不会悄悄退回 mock。
5. 需要至少配置 CROPFLOW_WEED_DIAGNOSIS_BASE_URL、CROPFLOW_PEST_DISEASE_SURVEY_BASE_URL、CROPFLOW_STAGE_PREDICTION_BASE_URL、CROPFLOW_WEATHER_API_BASE_URL、CROPFLOW_WEATHER_API_TOKEN。
6. 如果病虫调查窗口接口和病虫防治接口不是同一地址，再单独配置 CROPFLOW_PEST_DISEASE_CONTROL_BASE_URL。
```

## 4. 构建并启动

### 模式 A：compose 自带数据库

先启动数据库和 API：

```bash
docker compose up -d --build db api
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

### 模式 B：外部 PostgreSQL

只启动 API：

```bash
docker compose up -d --build api
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

## 5. 初始化演示数据

如果你要一套可直接演示的内置数据，执行：

```bash
docker compose --profile tools run --rm seed
```

说明：

```text
1. 该命令会先执行 alembic upgrade head。
2. 该命令会写入演示农场、演示计划和 mock 流程数据。
3. seed 容器本身不要求真实外部接口，因为它只负责初始化演示数据。
4. 该命令适合内部演示，不适合正式生产初始化。
```

如果你只需要最小必需参考数据，不要演示农场 / 计划 / 任务数据，执行：

```bash
docker compose --profile tools run --rm seed seed-reference
```

说明：

```text
1. 该命令会先执行 alembic upgrade head。
2. 只导入必要初始化数据：cf_code_dict、cf_crop_stage_dict、cf_rice_variety、pp_rice_control_window_level_1、cf_farm、cf_field、cf_farm_field_relation。
3. 不会创建演示种植计划、日历、任务、执行和复核数据。
4. 适合把新库初始化到“可运行但不带演示业务数据”的状态。
```

## 6. 可选启动 scheduler

如果你希望演示后台自动推进逻辑，再启动：

```bash
docker compose --profile jobs up -d scheduler
```

默认建议：

```text
1. 只做静态演示时，先不开 scheduler，避免数据被后台任务持续改写。
2. 需要演示天气刷新、调查推荐、到期任务生成时，再开启 scheduler。
```

如果是外部数据库部署，也使用同一条命令；前提是 `.env` 中的 `CROPFLOW_DATABASE_URL` 已指向目标库。

## 7. 常用命令

查看日志：

```bash
docker compose logs -f api
docker compose logs -f scheduler
docker compose logs -f db
```

停止服务：

```bash
docker compose down
```

连同数据卷一起清理：

```bash
docker compose down -v
```

只执行迁移：

```bash
docker compose run --rm api migrate
```

## 8. 当前默认行为

```text
1. API 容器启动前会等待数据库可连接。
2. API 容器默认执行 alembic upgrade head 后再启动 uvicorn。
3. scheduler 容器默认不重复执行 migration。
4. seed 容器会执行 migration 后再写入演示数据。
5. 日志写到容器内 /app/logs，并映射到 compose volume。
```

## 9. 通过 tunnel 先迁移结构和必要数据

如果你当前只能在本地通过 tunnel 连目标数据库，建议先在本地执行一次结构迁移和必要数据导入，再把 Docker 部署到服务器。

示意流程：

```text
1. 本地建立 tunnel，例如把目标库映射到 127.0.0.1:15432
2. 本地设置 CROPFLOW_DATABASE_URL=postgresql+psycopg://user:password@127.0.0.1:15432/dbname
3. 执行 alembic upgrade head
4. 执行 scripts/seed_reference_data.py
5. 确认目标库已有最新表结构、默认农场/地块/关联和基础参考数据
6. 再把服务器上的 .env 指向正式数据库地址，启动 docker compose
```

本地命令：

```powershell
$env:CROPFLOW_DATABASE_URL="postgresql+psycopg://user:password@127.0.0.1:15432/dbname"
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe scripts/seed_reference_data.py
```

如果希望用仓库脚本一键执行，改用：

```powershell
powershell -File scripts/bootstrap-db.ps1 `
  -DatabaseUrl "postgresql+psycopg://user:password@127.0.0.1:15432/dbname"
```

## 10. 风险提示

```text
1. 当前 compose 文件没有包含 Nginx，默认直接暴露 API 端口。
2. 当前演示环境主要面向内部使用，不包含 TLS、集中式 secret 管理或多副本部署。
3. 如果要进一步走准生产部署，再补反向代理、镜像发布、备份和监控。
```
