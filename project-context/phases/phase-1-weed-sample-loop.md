# Phase P1 - 杂草防治样板闭环

对应 roadmap：`T0 -> T1`

## 目标

```text
1. 冻结杂草防治样板闭环范围。
2. 冻结第一条样板链路的关键业务口径。
3. 收口接口摘要、字段草案、场景表和页面范围。
4. 收口当前阶段仍阻塞 P2 的待决事项。
```

## 范围

```text
1. PlantingPlan 创建后触发的土壤封闭和药前调查日历维护。
2. 调查类 CalendarItem 按统一时间窗进入正式任务。
3. 土壤封闭、药前调查、茎叶除草、药后调查、药害缓解、补防判断、服务评价主链路。
4. 前端第一条演示链路所需页面和字段范围。
5. 当前阶段闭环相关的数据对象和 DDL 草案。
```

## 当前关键交付物

```text
1. docs/history/P1/todo-list.md
2. docs/workflow/checklists/plant-protection-task-checklist.md
3. docs/domain/plant-protection.md
4. docs/frontend/overview.md
5. docs/api/weed_diagnosis_api.md
6. database/sql/20260518_weed_protection_closed_loop.sql
```

## 完成标准

```text
1. 植保范围、样板链路范围、验收标准均已冻结。
2. 植保接口摘要、字段草案、分支规则、复核规则齐备。
3. 上游链路和关键后台任务边界明确，且已同步到核心文档。
4. 前端页面清单、字段缺口、低保真原型和演示流程齐备。
5. 待决事项已有明确责任人和拍板结论。
```

## 状态

`mostly_done`
