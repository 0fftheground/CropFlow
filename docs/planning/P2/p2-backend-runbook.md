# P2 后端联调 Runbook

> 本文档用于在 P2 阶段重复执行本地后端、scheduler、seed、trace 和真实杂草算法联调。  
> 范围只覆盖当前已实现的杂草防治样板后端。

## 1. 启动前提

需要具备：

1. 本地 PostgreSQL 可连接
2. 已完成 migration
3. Python 环境可执行 `.venv\Scripts\python.exe`

数据库配置来源：

```text
1. 优先读取 CROPFLOW_DATABASE_URL
2. 否则读取 database/sql/db_config.json
```

## 2. 本地启动

### 2.1 启动 API

```powershell
scripts/start-dev.ps1 -Mode api -Port 8000
```

等价命令：

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2.2 启动 scheduler

```powershell
scripts/start-dev.ps1 -Mode scheduler
```

等价命令：

```powershell
python -m app.jobs.runner
```

## 3. 初始化本地数据

```powershell
.venv\Scripts\python.exe scripts/seed_local_dev_data.py
```

用途：

1. 准备联调所需基础数据
2. 预置示例计划和地块

## 4. 后端自检

### 4.1 健康检查

```powershell
curl http://127.0.0.1:8000/api/health
```

### 4.2 全量测试

```powershell
.venv\Scripts\python.exe -m pytest
```

## 5. Trace 脚本

### 5.1 杂草主链路 trace

```powershell
.venv\Scripts\python.exe scripts/run_e2e_trace.py
```

说明：

1. 会自动创建计划
2. 会跑药前调查、复核、执行、药后调查主链路
3. 结果写入 `project-context/session-log/e2e-traces/`

### 5.2 土壤封闭专项 trace

```powershell
.venv\Scripts\python.exe scripts/run_soil_treatment_trace.py
```

说明：

1. 会自动创建计划
2. 会验证土壤封闭建议、审核、正式任务、执行完成
3. 结果写入 `project-context/session-log/e2e-traces/`

## 6. 真实杂草算法联调

### 6.1 配置真实算法地址

设置：

```powershell
$env:CROPFLOW_WEED_DIAGNOSIS_BASE_URL="http://47.99.129.235:3319"
```

然后重新启动 API 或 scheduler。

### 6.2 运行真实算法集成测试

```powershell
$env:CROPFLOW_REAL_WEED_API_BASE_URL="http://47.99.129.235:3319"
.venv\Scripts\python.exe -m pytest tests/integration/test_real_weed_api.py
```

说明：

1. 默认不会跑真实外部测试
2. 只有设置 `CROPFLOW_REAL_WEED_API_BASE_URL` 后才会执行

## 7. 常见排查点

### 7.1 算法接口不可达

表现：

1. API 返回 `400` 或 `500`
2. 日志中出现 `Weed diagnosis API is unreachable`

处理：

1. 检查 `CROPFLOW_WEED_DIAGNOSIS_BASE_URL`
2. 检查目标地址可访问性

### 7.2 算法接口超时

表现：

1. 日志中出现 `Weed diagnosis API timed out`

处理：

1. 检查网络连通性
2. 检查算法服务响应时间

### 7.3 返回字段缺失

表现：

1. API 返回 `400`
2. `detail` 中包含 `did not return ...`

处理：

1. 对照 `docs/api/weed_diagnosis_api.md`
2. 检查算法服务当前返回结构

### 7.4 联调问题追踪

后端当前会回写：

```text
X-Request-ID
```

建议前后端联调时记录这个响应头，便于从日志中定位请求。
