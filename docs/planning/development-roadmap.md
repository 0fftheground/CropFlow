# CropFlow 推进节奏与阶段目标

> 本文档用于说明 CropFlow MVP 的阶段推进、进入分工开发的条件和第一条垂直闭环目标。  
> 系统架构见 `docs/overview/team-technical-briefing.md`，方向分工见 `docs/planning/team-work-division.md`。

---

# T0：当前阶段

当前处于逻辑数据模型和接口核对阶段。

近期目标：

```text
1. 完成 data-model.md 收敛。
2. 生成 ER 图。
3. 形成第一版表结构草案。
4. 形成第一版 API contract。
5. 确定第一条垂直闭环。
```

当前重点文档：

```text
docs/model/data-model.md
docs/model/data-model-validation.md
docs/workflow/task-workflow-matrix.md
docs/workflow/background-job-matrix.md
docs/api/
docs/planning/guides/agent-development-guidelines.md
```

---

# T1：开工前契约

进入分工开发前必须完成：

```text
1. ER 图。
2. 表结构草案。
3. API contract。
4. 技术栈和本地开发方式。
5. 前端页面清单。
6. 第一条垂直闭环验收标准。
7. AI agent 任务模板和代码交付规范。
```

完成后可以进入：

```text
1. 后端建表、迁移和核心接口开发。
2. 前端基于 mock API 开发主流程页面。
3. 各业务方向并行补算法接口适配和参数样例。
```

---

# T2：第一条垂直闭环

建议第一条闭环：

```text
PlantingPlan 创建
→ 生育期预测 / 农事日历
→ CalendarItem
→ FarmingTask
→ OperationPlan
→ ExecutionRecord / Feedback
→ ReviewRequest
```

第一条算法接入建议优先选择植保，因为当前已有接口文档。

后端重点：

```text
1. PlantingPlan 创建接口。
2. CalendarItem 生成或导入。
3. FarmingTask 生成。
4. OperationPlan 保存或生成。
5. ExecutionRecord / Feedback / ReviewRequest 最小链路。
```

前端重点：

```text
1. 计划创建页。
2. 计划详情页。
3. 农事项 / 任务列表。
4. 任务详情和方案查看。
5. 反馈和复核入口。
```

---

# T3：方向扩展

在第一条闭环稳定后，再并行扩展：

```text
1. 灌溉方向。
2. 施肥方向。
3. 遥感监测方向。
4. 更多植保分支。
5. 前端细化页面。
6. 后台任务和定时刷新。
```

扩展原则：

```text
1. 不改变核心任务模型。
2. 新增流程先更新 task-workflow-matrix。
3. 新增后台任务先更新 background-job-matrix。
4. 新增算法接口先补 docs/api。
5. 不稳定字段先进入 JSON 承接字段。
```
