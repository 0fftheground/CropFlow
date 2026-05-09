# CropFlow AI Agent 开发规范

> 本文档用于约束使用 AI agent 辅助开发 CropFlow 时的任务输入、代码交付、验证方式和禁止事项。  
> 全局项目规则见 `AGENTS.md`，方向分工见 `docs/planning/team-work-division.md`。

---

# 1. 使用场景

适用于以下开发任务：

```text
1. 核心后端模块开发。
2. 农事日历 / 生育期方向开发。
3. 植保、灌溉、施肥、遥感监测方向开发。
4. 前端页面和组件开发。
5. 算法 adapter、schema、mapper、rule、测试样例开发。
6. 文档与代码同步更新。
```

不适用于：

```text
1. 让 agent 自行重新设计核心架构。
2. 让 agent 未经确认新增核心对象。
3. 让 agent 绕过现有文档直接生成完整工程。
```

---

# 2. Agent 任务输入模板

给 agent 分配任务时，建议使用以下模板。

```text
任务方向：
核心后端 / 农事日历 / 植保 / 灌溉 / 施肥 / 遥感监测 / 前端

任务目标：
用 1-3 句话说明这次要实现什么。

必须阅读：
1. AGENTS.md
2. docs/overview/team-technical-briefing.md
3. docs/planning/team-work-division.md
4. docs/model/data-model.md
5. 与本方向相关的 docs/workflow/task-workflow-matrix.md / docs/workflow/background-job-matrix.md / docs/api/
6. 如任务涉及方向文档补齐，按 docs/planning/team-work-division.md 第 2.1 节模板提交。

允许修改：
列出本次允许修改的目录或文件。

禁止修改：
列出不能动的目录或文件，尤其是其他方向代码和核心模型。

预期代码交付：
adapter / schema / mapper / rule / service / API router / frontend component / tests

验收标准：
1. 需要通过哪些测试。
2. 需要生成哪些 mock 或 fixture。
3. 是否需要更新 OpenAPI。
4. 是否需要更新 docs。
5. 是否补齐 task 定义表、触发规则表、依赖关系表、算法接口模板和 JSON 样例。
```

---

# 3. 通用代码交付要求

除特别小的修复外，业务方向任务至少应提交：

```text
1. Adapter：外部算法或外部系统调用封装。
2. Schema / DTO：请求、响应、内部映射结构。
3. Mapper：算法结果到 OperationPlan / ExecutionRecord / Evaluation / Feedback / ReviewRequest 的映射。
4. Rule / Policy：是否生成任务、是否人工确认、是否触发后续动作。
5. Fixtures：算法响应、用户输入、执行反馈、异常场景样例。
6. Tests：adapter / mapper / rule 的单元测试，必要时补集成测试。
```

建议目录形态：

```text
backend/app/adapters/<direction>/
backend/app/schemas/<direction>/
backend/app/mappers/<direction>/
backend/app/rules/<direction>/
backend/app/services/<direction>/
backend/app/api/routes/<direction>.py
backend/tests/fixtures/<direction>/
backend/tests/unit/<direction>/
backend/tests/integration/<direction>/
```

前端建议目录形态：

```text
frontend/src/api/
frontend/src/mocks/
frontend/src/pages/
frontend/src/components/
frontend/src/tests/
```

---

# 4. 核心禁止事项

Agent 开发时必须遵守：

```text
1. 不新增与现有核心对象语义重复的对象。
2. 不把 CalendarItem 当成可执行任务。
3. 不让 Execution Module 创建 FarmingTask。
4. 不让 Feedback 直接创建 FarmingTask。
5. 不绕过 Plan Orchestrator 处理 ReviewRequestResolved。
6. 不把编排逻辑写进 Entity、ORM Model 或 Repository。
7. 不让业务方向各自定义一套任务、方案、执行或反馈模型。
8. 不擅自修改其他方向代码。
9. 不擅自生成完整工程框架，除非技术栈和工程结构已确认。
10. 不用临时字段替代已有核心模型字段。
```

---

# 5. 方向任务模板

## 5.1 核心后端 Agent

必须关注：

```text
1. 数据模型与迁移。
2. 通用 CRUD 和查询接口。
3. PlanOrchestrator 和 Handler 框架。
4. CalendarItem -> FarmingTask。
5. FarmingTask -> OperationPlan。
6. ExecutionRecord -> Feedback -> ReviewRequest。
```

预期代码交付：

```text
backend/app/models/
backend/app/schemas/common/
backend/app/modules/plan/
backend/app/modules/task/
backend/app/modules/execution/
backend/app/modules/feedback/
backend/app/modules/review/
backend/app/orchestrators/
backend/tests/
```

验收重点：

```text
1. 不把业务方向细节写死在核心模块。
2. 状态流转清楚。
3. 幂等键和 source 字段可追溯。
4. 通用接口能支撑前端 mock 和业务方向 adapter。
```

## 5.2 农事日历 / 生育期 Agent

预期代码交付：

```text
backend/app/adapters/stage/
backend/app/adapters/calendar/
backend/app/schemas/stage/
backend/app/schemas/calendar/
backend/app/mappers/calendar/
backend/app/rules/calendar/
backend/tests/fixtures/calendar/
backend/tests/unit/calendar/
backend/tests/integration/calendar/
```

验收重点：

```text
1. 生育期预测结果能映射为 StagePredictionSnapshot / CropStageState。
2. 农事日历结果能映射为 CalendarItem。
3. 生育期变化后能判断 CalendarItem 是否更新或失效。
4. 到期检查能判断是否生成 FarmingTask。
```

## 5.3 植保 Agent

预期代码交付：

```text
backend/app/adapters/plant_protection/
backend/app/schemas/plant_protection/
backend/app/mappers/plant_protection/
backend/app/rules/plant_protection/
backend/app/api/routes/plant_protection.py
backend/tests/fixtures/plant_protection/
backend/tests/unit/plant_protection/
backend/tests/integration/plant_protection/
```

验收重点：

```text
1. 调查结果录入后再调用诊断或防治推荐算法。
2. 防治方案映射到 OperationPlan。
3. 药后调查、补防判断和服务效果评估能映射到 Evaluation / Feedback。
4. 需要人工确认的结果生成 ReviewRequest，不直接生成 FarmingTask。
```

## 5.4 灌溉 Agent

预期代码交付：

```text
backend/app/adapters/irrigation/
backend/app/schemas/irrigation/
backend/app/mappers/irrigation/
backend/app/rules/irrigation/
backend/app/api/routes/irrigation.py
backend/tests/fixtures/irrigation/
backend/tests/unit/irrigation/
backend/tests/integration/irrigation/
```

验收重点：

```text
1. 灌溉推荐能映射到 OperationPlan。
2. 设备回调或人工反馈能映射到 ExecutionRecord。
3. 水位达标、异常、超时能映射到 Evaluation / Feedback。
4. 异常结果需要人工处理时生成 ReviewRequest。
```

## 5.5 施肥 Agent

预期代码交付：

```text
backend/app/adapters/fertilization/
backend/app/schemas/fertilization/
backend/app/mappers/fertilization/
backend/app/rules/fertilization/
backend/app/api/routes/fertilization.py
backend/tests/fixtures/fertilization/
backend/tests/unit/fertilization/
backend/tests/integration/fertilization/
```

验收重点：

```text
1. 施肥方案能映射到 OperationPlan。
2. 变量处方图能进入 prescriptionMap。
3. 施肥执行结果能映射到 ExecutionRecord。
4. 穗肥效果抽查能映射到 Evaluation / Feedback。
5. 肥料实际消耗能和库存流水衔接。
```

## 5.6 遥感监测 Agent

预期代码交付：

```text
backend/app/adapters/remote_sensing/
backend/app/schemas/remote_sensing/
backend/app/mappers/remote_sensing/
backend/app/rules/remote_sensing/
backend/app/api/routes/remote_sensing.py
backend/tests/fixtures/remote_sensing/
backend/tests/unit/remote_sensing/
backend/tests/integration/remote_sensing/
```

验收重点：

```text
1. 缺苗识别、长势监测、NDVI 结果能映射到 Evaluation / Feedback。
2. 影像上传、拼接、算法处理过程能映射到 ExecutionRecord。
3. 缺苗识别异常能触发 ReviewRequest 或后续任务意图。
4. 穗肥前长势监测结果能衔接施肥 OperationPlan 的变量处方图。
```

## 5.7 前端 Agent

预期代码交付：

```text
frontend/src/api/
frontend/src/mocks/
frontend/src/pages/plan/
frontend/src/pages/tasks/
frontend/src/components/operation-plan/
frontend/src/components/execution-record/
frontend/src/components/evaluation-feedback/
frontend/src/pages/review/
frontend/src/pages/remote-sensing/
frontend/src/pages/inventory/
frontend/src/tests/
```

验收重点：

```text
1. CalendarItem 和 FarmingTask 在页面上明确区分。
2. OperationPlan 能展示不同方向的 parameters / prescriptionMap / operationArea。
3. ExecutionRecord / Feedback / ReviewRequest 能形成闭环页面。
4. 前端基于 OpenAPI 或 mock 数据，不自行发明字段。
```

---

# 6. Agent 完成任务检查清单

每个 agent 任务完成前必须自查：

```text
1. 是否只修改了任务允许的文件。
2. 是否符合 AGENTS.md 的核心设计。
3. 是否没有新增重复核心对象。
4. 是否没有绕过 Plan Orchestrator。
5. 是否补齐 schema、mapper、rule、fixture、test。
6. 是否更新相关 docs 或说明不需要更新。
7. 是否运行了与修改范围匹配的测试。
8. 是否在结果说明中列出改动文件、测试结果和剩余风险。
```

---

# 7. 架构负责人 Review 清单

架构负责人 Review agent 输出时重点看：

```text
1. 有没有破坏模块边界。
2. 有没有新增重复概念。
3. OperationPlan / ExecutionRecord / Evaluation / Feedback 的映射是否清楚。
4. 是否把业务方向规则写进了核心通用模块。
5. 是否缺少异常场景和人工复核场景。
6. 是否有可运行测试或足够明确的 mock / fixture。
7. 是否需要同步更新 data-model、task-workflow-matrix、background-job-matrix 或 API 文档。
```
