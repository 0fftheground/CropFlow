# CropFlow Wiki Index

本文件是正式项目文档的导航页，用于把长期系统知识、当前工作状态和变更沉淀放到可发现的位置。

说明：

```text
1. 这里做索引，不复制完整事实。
2. 长期稳定知识放 docs/ 下的正式文档。
3. 当前工作状态放 project-context/current-memory.md。
4. 任务完成后的演进摘要放 docs/change-notes/。
```

## Current Work

- `project-context/current-memory.md`
- `project-context/development-plan.md`
- `project-context/phases/`

## Shared Entrypoints

- `AGENTS.md`
- `docs/ai/README.md`
- `docs/ai/codex-skill-workflow.md`
- `project-context/entrypoints.md`
- `docs/README.md`

## Architecture

- `docs/overview/team-technical-briefing.md`
- `docs/architecture/system-function.md`
- `docs/architecture/architecture.md`
- `docs/architecture/modules.md`
- `docs/architecture/events.md`
- `docs/architecture/data-integration.md`
- `docs/architecture/orchestration-design.md`
- `docs/architecture/agent-runtime.md`
- `docs/architecture/agent-runtime-durable-execution.md`

## Domain And Data Model

- `docs/domain/README.md`
- `docs/domain/calendar-stage.md`
- `docs/domain/plant-protection.md`
- `docs/domain/irrigation.md`
- `docs/domain/fertilization.md`
- `docs/domain/remote-sensing.md`
- `docs/model/domain-model.md`
- `docs/model/data-model.md`
- `docs/model/data-model-validation.md`
- `docs/model/glossary.md`

## Workflows

- `docs/workflow/task-workflow-matrix.md`
- `docs/workflow/background-job-matrix.md`
- `docs/workflow/flows/plan-creation-initialization.md`
- `docs/workflow/flows/runtime-event-task-update.md`
- `docs/workflow/flows/task-execution-feedback.md`

## API Contracts

- `docs/api/frontend-plant-protection-api-contract.md`
- `docs/api/weed_diagnosis_api.md`
- `docs/api/growth_stage_gdd_api.md`
- `docs/api/pestDisease_survey_window_api.md`
- `docs/api/pestDisease_control_window_api.md`
- `docs/api/fertilization_prescription_algorithm_api.md`
- `docs/api/agent_runtime_api.md`

## Decisions

- `docs/decisions/001-plan-level-mvp.md`
- `docs/decisions/002-remove-recommendation-entity.md`
- `docs/decisions/003-taskintent-before-farmingtask.md`
- `docs/decisions/004-feedback-back-to-plan-orchestrator.md`
- `docs/decisions/005-external-execution-system-boundary.md`
- `docs/decisions/006-orchestrator-internal-layering.md`
- `docs/decisions/007-stage-weather-runtime-mvp-rules.md`
- `docs/decisions/008-calendaritem-farmingtask-operationplan-boundary.md`
- `docs/decisions/009-calendaritem-task-generation-without-taskgenerationplan.md`
- `docs/decisions/010-inventory-first-class-model.md`
- `docs/decisions/011-disease-pest-review-theory-plan-only.md`
- `docs/decisions/012-agent-runtime-business-state-boundary.md`
- `docs/decisions/013-agent-runtime-tool-concurrency-policy.md`
- `docs/decisions/014-agent-runtime-tool-failure-reinjection.md`
- `docs/decisions/015-agent-runtime-model-eval-governance.md`
- `docs/decisions/016-agent-runtime-provider-retry-and-run-budget.md`
- `docs/decisions/017-agent-runtime-postgres-durable-worker.md` (Proposed)

## Change Notes

- `docs/change-notes/README.md`
- `docs/change-notes/2026-06-08-weather-stage-runtime-stabilization.md`
- `docs/change-notes/2026-06-11-remote-db-bootstrap-and-docker-deploy.md`
- `docs/change-notes/2026-06-18-disease-pest-review-theory-plan-adjustments.md`
- `docs/change-notes/2026-06-22-docs-knowledge-structure-reorganization.md`
- `docs/change-notes/2026-06-23-farm-field-management-api.md`
- `docs/change-notes/2026-06-23-models-module-split.md`
- `docs/change-notes/2026-07-18-agent-runtime-integration.md`
- `docs/change-notes/2026-07-18-agent-runtime-parallel-query-batches.md`
- `docs/change-notes/2026-07-18-agent-runtime-tool-failure-reinjection.md`
- `docs/change-notes/2026-07-18-agent-runtime-eval-v2.md`
- `docs/change-notes/2026-07-18-agent-runtime-resilience-budgets.md`

## Development Guides

- `docs/development/local-dev-runbook.md`
- `docs/development/agent-runtime-model-eval.md`
- `docs/development/remote-db-bootstrap.md`
- `docs/development/docker-demo-deploy.md`
- `docs/fde/README.md`
- `docs/fde/fde-standard-workflow.md`
- `docs/fde/agri-task-integration-doc-requirements.md`
- `docs/frontend/README.md`
- `docs/frontend/overview.md`
- `docs/frontend/plant-protection-handoff.md`
- `docs/maintenance/docs-hygiene-plan.md`
- `docs/history/README.md`
