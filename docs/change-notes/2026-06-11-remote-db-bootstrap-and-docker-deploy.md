# 2026-06-11 Remote DB Bootstrap And Docker Deploy

## Summary

补齐远程数据库初始化、基础参考数据导入、农场地块迁移和 Docker 演示部署路径，使后端不再依赖临时手工步骤才能拉起。

## Code Changes

- 新增 `scripts/bootstrap-db.ps1`，统一 migration、seed 和可选农场地块迁移。
- 新增 `scripts/seed_reference_data.py`、`scripts/migrate_farm_field_data.py`。
- 新增 `Dockerfile`、`docker-compose.yml`、`docker/entrypoint.sh`、`.env.docker.example`。

## Business Logic Changes

- 新库可以先初始化到“可运行但不带演示业务数据”的状态。
- 远程数据库初始化与容器拉起路径被沉淀为标准步骤，不再依赖一次性口头说明。
- 演示环境与外部 PostgreSQL 部署路径被明确区分。

## Affected Areas

- `docs/development/remote-db-bootstrap.md`
- `docs/development/docker-demo-deploy.md`
- `scripts/bootstrap-db.ps1`
- `scripts/seed_reference_data.py`
- `scripts/migrate_farm_field_data.py`
- `Dockerfile`
- `docker-compose.yml`

## Tests

本次为历史变更补档，当前没有重新执行部署验证。当前说明以正式 runbook 和已合入脚本为准。

## Remaining Assumptions

- 当前容器化入口主要面向内部演示和联调，不等同于完整生产部署方案。
- 远程机器镜像源、反向代理和监控仍需按环境单独补充。

## Manual Review Checklist

- 确认 `bootstrap-db.ps1` 能完成 migration 和最小 seed。
- 确认外部 PostgreSQL 模式下 API / scheduler 只依赖 `CROPFLOW_DATABASE_URL`。
- 确认演示环境和 reference 初始化模式的边界没有混淆。

## Related Documents

- `docs/development/remote-db-bootstrap.md`
- `docs/development/docker-demo-deploy.md`
