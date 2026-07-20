# 2026-06-18 Disease Pest Review TheoryPlan Adjustments

## Summary

收口病虫害防治复核契约：人工审核只处理 `theoryPlan`，支持整表提交 `rounds` 的增删改，并由后端统一重算实际防治窗口和正式方案。

## Code Changes

- `/api/review-requests/{reviewRequestId}/resolve` 对 `plant_protection.disease_pest_control` 只接受 `decision_payload.proposedPlan.theoryPlan`。
- `theoryPlan.rounds` 支持按完整列表提交，后端按整组替换处理新增、删除和重排。
- 病虫害详情与复核详情补齐中文 `targets` key 和 `reviewContext.availableTargets`。

## Business Logic Changes

- 审核阶段不再直接改正式 `controlPlan`。
- 最终 `recommendedControlDate`、`operationWindow`、`controlPlan` 都从审核后的 `theoryPlan` 派生。
- 常规调查和突发调查合并后的病虫害建议，统一通过同一条复核口径收口。

## Affected Areas

- `project-context/current-memory.md`
- `docs/api/frontend-plant-protection-api-contract.md`
- `docs/frontend/plant-protection-handoff.md`
- `docs/workflow/flows/plant-protection-disease-pest-loop.md`
- `tests/services/test_review_request_service.py`
- `tests/api/test_review_requests.py`
- `tests/api/test_task_details.py`

## Tests

当时已补齐并通过：

```text
tests/services/test_review_request_service.py
tests/api/test_review_requests.py
tests/api/test_task_details.py
```

## Remaining Assumptions

- 真实前端联调仍需继续验证 `theoryPlan.rounds` 整表提交流程。
- 当前正式防治执行完成后，还没有像杂草链路那样继续自动生成药后调查。

## Manual Review Checklist

- 确认前端只提交 `proposedPlan.theoryPlan`。
- 确认新增 / 删除轮次后，后端会自动重排轮次并重算实际窗口。
- 确认详情接口返回的 `targets` key 仍保持中文对象名口径。

## Related Documents

- `docs/decisions/011-disease-pest-review-theory-plan-only.md`
- `docs/api/frontend-plant-protection-api-contract.md`
- `docs/frontend/plant-protection-handoff.md`
- `docs/workflow/flows/plant-protection-disease-pest-loop.md`
