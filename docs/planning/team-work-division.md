# CropFlow 团队分工说明

> 本文档用于说明 CropFlow MVP 各方向的职责边界、近期任务和交付物。  
> 系统架构和核心流转见 `docs/overview/team-technical-briefing.md`，阶段推进见 `docs/planning/development-roadmap.md`。  
> 使用 AI agent 分工开发时，任务模板和验收规则见 `docs/planning/agent-development-guidelines.md`。

---

# 1. 分工原则

团队按业务方向推进，但核心平台统一收口。

```text
1. 核心对象、模块边界、API contract 由核心后端和产品 / 架构负责人统一把控。
2. 各业务方向负责自己的业务流程、算法适配、OperationPlan 映射、执行结果和评价反馈规则。
3. 核心后端负责通用模型、通用接口、状态流转、幂等、审计和落库实现。
4. 前端可以基于 OpenAPI 和 mock 数据并行推进。
5. 不同方向不能各自发明一套任务、方案、执行和反馈模型。
```

---

# 2. 通用职责边界

## 2.1 业务方向负责什么

植保、灌溉、施肥、遥感监测、农事日历 / 生育期方向都需要围绕统一对象补齐本方向的业务细节。

| 责任项 | 说明 |
|---|---|
| 农事项定义 | 明确本方向有哪些 `taskCategory / taskSubtype`、触发条件和前后依赖 |
| 算法接口 | 提供接口文档、请求 / 响应样例、异常返回、字段含义 |
| 任务生成 | 说明什么情况下生成 `CalendarItem / TaskIntent / FarmingTask` |
| 作业方案 | 定义本方向 `OperationPlan.parameters / operationArea / prescriptionMap / acceptanceCriteria` |
| 执行过程 | 定义执行方式、执行主体、执行结果、附件、轨迹或设备回调字段 |
| 评价反馈 | 定义本方向如何形成 `Evaluation.metrics`、`Feedback.details`、是否需要人工复核 |
| 测试样例 | 至少提供 1 个正常样例、1 个异常或需复核样例、1 个不生成任务或无需动作样例 |

## 2.2 核心后端负责什么

核心后端不替各业务方向定义农艺规则，但负责把各方向收敛到统一模型和接口中。

| 责任项 | 说明 |
|---|---|
| 数据模型 | 实现 `PlantingPlan / CalendarItem / TaskIntent / FarmingTask / OperationPlan / Execution / Feedback / ReviewRequest` 等通用表结构 |
| API contract | 设计统一 REST API 和 OpenAPI，支持前端和各方向联调 |
| 编排框架 | 实现最小 `PlanOrchestrator`、事件 Handler、状态流转 |
| 任务框架 | 实现 CalendarItem 到 FarmingTask、TaskIntent 到 FarmingTask、OperationPlan 版本管理 |
| 执行框架 | 实现 Execution、ExecutionRecord、DeviceCommand 的通用接口和状态 |
| 反馈复核 | 实现 Evaluation / Feedback / ReviewRequest 的通用落库和回编排机制 |
| 集成适配 | 为农事日历、植保、灌溉、施肥、遥感监测提供算法适配器接入点 |

## 2.3 代码提交形态

下面路径是建议形态，用于说明每个方向应该提交什么类型的代码。实际工程骨架确定后，以后端和前端项目中的真实目录为准。

| 代码类型 | 说明 | 建议位置 |
|---|---|---|
| Adapter | 调用外部算法或第三方系统，处理请求、响应、错误和超时 | `backend/app/adapters/<direction>/` |
| DTO / Schema | 定义算法请求、算法响应、前端请求、前端响应的数据结构 | `backend/app/schemas/<direction>/` |
| Mapper | 把算法结果映射成 `OperationPlan / Evaluation / Feedback / ReviewRequest` 所需结构 | `backend/app/mappers/<direction>/` |
| Rule / Policy | 判断是否生成任务、是否需要人工确认、是否需要后续动作 | `backend/app/rules/<direction>/` |
| Service | 组合 adapter、mapper、rule，形成方向内业务服务 | `backend/app/services/<direction>/` |
| API Router | 如需要方向专用录入接口，提供 REST API | `backend/app/api/routes/<direction>.py` |
| Test Fixtures | 请求样例、响应样例、算法 mock、执行反馈样例 | `backend/tests/fixtures/<direction>/` |
| Unit Tests | 测试 adapter、mapper、rule 的稳定行为 | `backend/tests/unit/<direction>/` |
| Integration Tests | 测试从任务到方案、执行、反馈、复核的链路 | `backend/tests/integration/<direction>/` |
| Frontend Components | 方向相关页面、表单、详情展示和 mock 数据 | `frontend/src/...` |

业务方向最少应提交：

```text
1. 算法 adapter。
2. 请求 / 响应 schema。
3. OperationPlan mapper。
4. ExecutionRecord / Evaluation / Feedback mapper 或字段构造函数。
5. 是否生成任务、是否人工确认、是否后续处理的 rule。
6. mock 数据和至少 3 个测试场景。
```

---

# 3. 产品 / 架构负责人

负责人：All。

主要职责：

```text
1. 维护领域口径、核心对象和模块边界。
2. 确认业务规则、流程分支和接口优先级。
3. 判断新增需求是否进入 MVP。
4. Review 文档、表结构、API contract 和 PR 是否违反核心设计。
5. 组织每个方向补齐算法接口、OperationPlan 映射、执行反馈和评价规则。
```

需要重点确认：

```text
1. 每个农事项是否需要生成 CalendarItem、FarmingTask、OperationPlan。
2. 哪些算法结果可以自动转任务，哪些必须人工确认。
3. 哪些执行结果会触发 Feedback、ReviewRequest 或后续任务。
4. 哪些字段需要结构化，哪些第一版先放 JSON。
5. 第一条垂直闭环的验收标准。
```

近期交付物：

```text
1. docs/model/data-model.md 最终确认。
2. docs/workflow/task-workflow-matrix.md 业务流程确认。
3. docs/workflow/background-job-matrix.md 后台任务确认。
4. 第一条垂直闭环验收标准。
5. 各方向提交物 Review 结论。
```

---

# 4. 核心后端方向

建议负责人：后端主责。

主要职责：

```text
1. 建立 FastAPI 工程结构。
2. 建立 PostgreSQL 表结构和 Alembic 迁移。
3. 实现 Farm / Field / PlantingPlan 基础接口。
4. 实现 CalendarItem / TaskIntent / FarmingTask / OperationPlan 基础模型。
5. 实现 Execution / ExecutionRecord / Evaluation / Feedback / ReviewRequest 基础模型。
6. 实现 EventRecord、幂等键、状态流转、审计字段。
7. 实现最小 PlanOrchestrator 和 Handler 框架。
8. 提供 OpenAPI、mock 数据和种子数据。
```

需要交付的通用能力：

| 能力 | 说明 |
|---|---|
| 计划能力 | 创建、查询、更新计划状态 |
| 预备农事项能力 | 生成、查询、失效、重算 CalendarItem |
| 正式任务能力 | 创建、确认、取消、完成 FarmingTask |
| 作业方案能力 | 创建 OperationPlan、版本管理、激活 / 失效 |
| 执行能力 | 创建 Execution、记录 ExecutionRecord、接收回调或人工反馈 |
| 评价反馈能力 | 保存 Evaluation / Feedback，并触发 Plan Orchestrator |
| 复核能力 | 创建 ReviewRequest、处理结论、回到 Plan Orchestrator |
| 算法适配能力 | 为各方向提供统一 adapter 接口和错误处理 |

近期交付物：

```text
1. 后端项目骨架和本地启动说明。
2. 第一版数据库迁移脚本。
3. OpenAPI 草案和 mock 数据。
4. 核心对象 CRUD / 查询接口。
5. PlanCreated 到 CalendarItem 的最小链路。
6. CalendarItem 到 FarmingTask 的最小链路。
7. FarmingTask 到 OperationPlan 的最小链路。
8. ExecutionRecord / Feedback / ReviewRequest 最小闭环。
9. 各业务方向 adapter 的接口占位和样例实现。
```

代码交付物：

```text
1. backend/app/main.py 或等价应用入口。
2. backend/app/db/ 数据库连接、基础模型、迁移配置。
3. backend/app/models/ 核心 ORM 模型。
4. backend/app/schemas/common/ 通用 DTO。
5. backend/app/modules/plan/ 计划基础能力。
6. backend/app/modules/task/ CalendarItem / TaskIntent / FarmingTask / OperationPlan 通用能力。
7. backend/app/modules/execution/ Execution / ExecutionRecord / DeviceCommand 通用能力。
8. backend/app/modules/feedback/ Evaluation / Feedback 通用能力。
9. backend/app/modules/review/ ReviewRequest / SystemNotification 通用能力。
10. backend/app/orchestrators/ PlanOrchestrator 和基础 Handler。
11. backend/app/adapters/base.py 外部算法 adapter 基类或协议。
12. backend/tests/ 覆盖核心对象和第一条闭环的测试。
```

不要做：

```text
1. 不先做复杂规则后台。
2. 不把编排逻辑写进 Entity 或 Repository。
3. 不让 Execution Module 直接创建 FarmingTask。
4. 不替业务方向臆造算法字段和农艺规则。
5. 不为了未来扩展提前做复杂框架。
```

---

# 5. 农事日历 / 生育期方向

主要职责：

```text
1. 对接生育期预测接口。
2. 对接农事日历接口。
3. 明确 stageCode 和 taskSubtype 映射。
4. 定义 CalendarItem 的生成、更新、失效和重算规则。
5. 定义生育期变化后哪些 CalendarItem / FarmingTask / OperationPlan 会受影响。
6. 定义 TaskDueCheckJob 如何把到期 CalendarItem 转为 FarmingTask。
```

需要补齐的内容：

| 类型 | 需要说明 |
|---|---|
| 输入 | PlantingPlan、品种、播期、移栽信息、地块、气象或积温数据 |
| 输出 | StagePredictionSnapshot、CropStageState、CalendarItem |
| OperationPlan 关系 | 农事日历通常不直接生成具体作业参数，但需要说明哪些农事项后续必须生成 OperationPlan |
| 执行关系 | 说明哪些 CalendarItem 到期后应生成可执行 FarmingTask |
| 评价反馈关系 | 说明生育期偏差、计划变更、实际阶段录入后是否需要重算或复核 |

近期交付物：

```text
1. 生育期预测接口适配说明。
2. 农事日历接口适配说明。
3. stageCode 清单。
4. taskCategory / taskSubtype 映射表。
5. CalendarItem 生成规则样例。
6. 生育期变化影响范围说明。
7. CalendarItem 到 FarmingTask 的生成条件样例。
8. 至少 3 个测试场景：计划初始化、天气变化、人工录入真实生育期。
```

代码交付物：

```text
1. backend/app/adapters/stage/stage_prediction_adapter.py
2. backend/app/adapters/calendar/agronomy_calendar_adapter.py
3. backend/app/schemas/stage/ 生育期预测请求和响应 DTO。
4. backend/app/schemas/calendar/ 农事日历请求和响应 DTO。
5. backend/app/mappers/calendar/calendar_item_mapper.py
6. backend/app/rules/calendar/calendar_refresh_policy.py
7. backend/app/rules/calendar/task_due_policy.py
8. backend/tests/fixtures/calendar/ 计划初始化、天气变化、真实生育期录入样例。
9. backend/tests/unit/calendar/ CalendarItem 映射和失效规则测试。
10. backend/tests/integration/calendar/ PlanCreated 到 CalendarItem 的链路测试。
```

---

# 6. 植保方向

主要职责：

```text
1. 对接 soil_treatment_diagnosis。
2. 对接 weed_treatment_diagnosis。
3. 对接 after_treatment_diagnosis。
4. 对接 additional_treatment_diagnosis。
5. 对接 /api/get_control_plan。
6. 定义植保调查、诊断、防治、药后调查、补防、服务效果评估的任务流转。
7. 定义植保 OperationPlan.parameters / prescriptionMap / acceptanceCriteria。
8. 定义植保执行记录、评价反馈和人工复核规则。
```

当前已确认：

```text
1. soil_treatment_diagnosis 返回土壤封闭推荐日期和茎叶除草药前调查日期。
2. weed_treatment_diagnosis 在药前调查结果录入后调用。
3. 病虫防治推荐算法在调查结果录入后调用，不挂在病虫防治作业流程下。
4. /api/get_control_plan 返回最终处方，映射到 OperationPlan.parameters。
5. additional_treatment_diagnosis 返回立即补防时，必须人工确认后才能生成补防任务。
```

需要补齐的内容：

| 类型 | 需要说明 |
|---|---|
| 任务 | 土壤封闭、茎叶除草药前调查、防治作业、药后调查、补防、病虫调查、防治实施、服务效果评估 |
| 算法 | 每个算法的触发时机、输入来源、输出字段、是否需要人工确认 |
| OperationPlan | 药剂、剂型、厂家、推荐用量、兑水量、作业区域、处方数组、推荐防治日期、方案依据 |
| 执行 | 防治实施的作业前水层、作业过程、作业后水层、执行反馈、附件或轨迹字段 |
| Evaluation | 药害识别、药后调查、服务效果评估、异常点位、评价指标 |
| Feedback | 是否完成、是否异常、是否需要补防、是否需要人工复核、后续任务建议 |

近期交付物：

```text
1. 植保算法接口适配说明。
2. 植保调查结果录入 API contract。
3. 植保防治 OperationPlan JSON 样例。
4. 药后调查 ExecutionRecord / Evaluation / Feedback 样例。
5. 补防人工确认流程和 ReviewRequest 样例。
6. 病虫调查到防治任务的转换规则。
7. 至少 3 个端到端测试场景：
   - 茎叶除草药前调查后生成防治方案。
   - 药后调查识别异常并触发补防人工确认。
   - 病虫调查结果不需要防治，只记录 NoAction。
```

代码交付物：

```text
1. backend/app/adapters/plant_protection/soil_treatment_diagnosis_adapter.py
2. backend/app/adapters/plant_protection/weed_treatment_diagnosis_adapter.py
3. backend/app/adapters/plant_protection/after_treatment_diagnosis_adapter.py
4. backend/app/adapters/plant_protection/additional_treatment_diagnosis_adapter.py
5. backend/app/adapters/plant_protection/control_plan_adapter.py
6. backend/app/schemas/plant_protection/ 植保算法请求、响应、调查录入 DTO。
7. backend/app/mappers/plant_protection/operation_plan_mapper.py
8. backend/app/mappers/plant_protection/evaluation_feedback_mapper.py
9. backend/app/rules/plant_protection/control_decision_policy.py
10. backend/app/rules/plant_protection/additional_treatment_review_policy.py
11. backend/app/api/routes/plant_protection.py，如需要植保调查录入接口。
12. backend/tests/fixtures/plant_protection/ 各算法 mock 响应和调查样例。
13. backend/tests/unit/plant_protection/ adapter、mapper、rule 测试。
14. backend/tests/integration/plant_protection/ 调查到方案、药后调查到补防复核链路测试。
```

---

# 7. 灌溉方向

主要职责：

```text
1. 补充灌溉算法接口文档。
2. 明确灌溉任务类型、触发条件和执行流程。
3. 明确灌溉 OperationPlan.parameters。
4. 明确是否需要 operationArea / prescriptionMap。
5. 明确执行模式：人工、设备、第三方系统。
6. 明确设备回调、轮询和人工反馈的数据格式。
7. 定义灌溉 Evaluation / Feedback 规则。
```

需要补齐的内容：

| 类型 | 需要说明 |
|---|---|
| 任务 | 灌溉任务、排水任务、水层保持、晒田相关任务与计划阶段关系 |
| 算法 | 推荐水量、推荐时间、推荐区域、传感器或气象输入 |
| OperationPlan | 水量、水位目标、执行窗口、田块区域、设备参数、验收标准 |
| 执行 | 人工执行、设备执行、第三方执行的 ExecutionRecord 字段 |
| Evaluation | 实际水位、水层保持结果、执行是否超时、设备是否异常 |
| Feedback | 完成、未完成、异常、需要人工处理、需要重新灌溉或调整计划 |

近期交付物：

```text
1. 灌溉算法接口文档。
2. 灌溉 OperationPlan JSON 样例。
3. 灌溉执行反馈 ExecutionRecord 样例。
4. 设备回调 / 轮询字段说明。
5. 灌溉 Evaluation.metrics 样例。
6. 灌溉 Feedback.details 样例。
7. 至少 3 个测试场景：
   - 算法推荐灌溉并生成 OperationPlan。
   - 设备执行成功并生成 Feedback completed。
   - 设备异常或水位不达标并触发 ReviewRequest。
```

代码交付物：

```text
1. backend/app/adapters/irrigation/irrigation_recommendation_adapter.py
2. backend/app/schemas/irrigation/ 灌溉算法请求、响应、设备回调 DTO。
3. backend/app/mappers/irrigation/operation_plan_mapper.py
4. backend/app/mappers/irrigation/execution_record_mapper.py
5. backend/app/mappers/irrigation/evaluation_feedback_mapper.py
6. backend/app/rules/irrigation/water_level_policy.py
7. backend/app/rules/irrigation/execution_exception_policy.py
8. backend/app/api/routes/irrigation.py，如需要水位或人工反馈录入接口。
9. backend/tests/fixtures/irrigation/ 推荐、执行成功、执行异常样例。
10. backend/tests/unit/irrigation/ 灌溉方案映射、反馈规则测试。
11. backend/tests/integration/irrigation/ 推荐到执行反馈、异常到复核链路测试。
```

---

# 8. 施肥方向

主要职责：

```text
1. 补充施肥算法接口文档。
2. 区分基肥、分蘖肥、穗肥、发苗肥、促芽肥等参数。
3. 明确穗肥前长势监测到变量处方图的关系。
4. 明确是否需要 prescriptionMap。
5. 明确肥料类型、用量、面积、作业窗口和验收标准。
6. 明确施肥作业执行记录、效果抽查和反馈规则。
7. 明确施肥与库存物料的关系。
```

需要补齐的内容：

| 类型 | 需要说明 |
|---|---|
| 任务 | 基肥、分蘖肥、穗肥、穗肥效果抽查、再生季发苗肥、促芽肥 |
| 算法 | 施肥量、变量处方图、推荐时间、推荐区域、长势监测输入 |
| OperationPlan | 肥料品类、用量、单位、作业区域、处方图、执行窗口、验收标准 |
| 执行 | 作业前水层、施肥作业、作业后水层、农事作业反馈 |
| Evaluation | 穗肥效果抽查、长势变化、处方执行偏差 |
| Feedback | 完成、异常、效果不足、需要复核、是否影响后续农事 |
| 库存 | 肥料库存查询、实际消耗、出库流水 |

近期交付物：

```text
1. 施肥算法接口文档。
2. 基肥 / 分蘖肥 / 穗肥 OperationPlan JSON 样例。
3. 变量处方图 prescriptionMap 样例。
4. 施肥 ExecutionRecord 样例。
5. 穗肥效果抽查 Evaluation.metrics 样例。
6. 施肥 Feedback.details 样例。
7. 肥料库存扣减字段说明。
8. 至少 3 个测试场景：
   - 常规施肥生成 OperationPlan 并完成执行反馈。
   - 穗肥前长势监测生成变量处方图。
   - 穗肥效果抽查发现异常并触发 ReviewRequest。
```

代码交付物：

```text
1. backend/app/adapters/fertilization/fertilization_recommendation_adapter.py
2. backend/app/schemas/fertilization/ 施肥算法请求、响应、执行反馈 DTO。
3. backend/app/mappers/fertilization/operation_plan_mapper.py
4. backend/app/mappers/fertilization/prescription_map_mapper.py
5. backend/app/mappers/fertilization/execution_record_mapper.py
6. backend/app/mappers/fertilization/evaluation_feedback_mapper.py
7. backend/app/rules/fertilization/fertilizer_inventory_policy.py
8. backend/app/rules/fertilization/topdressing_effect_policy.py
9. backend/app/api/routes/fertilization.py，如需要施肥反馈或抽查录入接口。
10. backend/tests/fixtures/fertilization/ 基肥、分蘖肥、穗肥、效果抽查样例。
11. backend/tests/unit/fertilization/ 方案映射、库存扣减、效果反馈规则测试。
12. backend/tests/integration/fertilization/ 变量处方图到施穗肥方案、抽查到复核链路测试。
```

---

# 9. 遥感监测方向

主要职责：

```text
1. 明确遥感监测任务类型、触发条件和执行流程。
2. 对接缺苗识别、长势监测、NDVI 长势监测、异常点位识别等算法。
3. 定义遥感监测 OperationPlan.parameters / operationArea / prescriptionMap / acceptanceCriteria。
4. 定义影像上传、影像拼接、算法处理、结果回写的执行记录字段。
5. 明确缺苗识别结果、长势监测结果与后续任务或方案的关系。
6. 定义遥感 Evaluation / Feedback 规则。
7. 明确长势监测与穗肥变量处方图的关系。
```

需要补齐的内容：

| 类型 | 需要说明 |
|---|---|
| 任务 | 缺苗识别、长势监测、穗肥前长势监测、穗肥后效果抽查、异常点位调查 |
| 算法 | 影像输入、拼接结果、NDVI 结果、缺苗区域、长势等级、异常点位 |
| OperationPlan | 航拍时间、影像类型、监测区域、监测目的、算法参数、验收标准 |
| 执行 | 无人机航测、影像上传、影像拼接、算法处理、结果确认的 ExecutionRecord 字段 |
| Evaluation | 缺苗面积、缺苗严重程度、长势等级变化、异常点位数量、处方图质量 |
| Feedback | 是否完成监测、是否需要补拍、是否需要人工确认、是否触发后续农事或处方生成 |
| 下游关系 | 缺苗识别可触发补苗或复核；穗肥前长势监测可为施穗肥 OperationPlan 提供变量处方图 |

近期交付物：

```text
1. 遥感监测算法接口文档。
2. 缺苗识别 OperationPlan JSON 样例。
3. 长势监测 OperationPlan JSON 样例。
4. 影像上传 / 影像拼接 / 算法处理 ExecutionRecord 样例。
5. 缺苗识别 Evaluation.metrics / Feedback.details 样例。
6. 长势监测 Evaluation.metrics / Feedback.details 样例。
7. 穗肥变量处方图与施肥 OperationPlan 的数据衔接说明。
8. 至少 3 个测试场景：
   - 缺苗识别生成缺苗区域重大事件或复核事项。
   - 常规长势监测生成长势状态更新和异常点位。
   - 穗肥前长势监测生成变量处方图并供施穗肥方案使用。
```

代码交付物：

```text
1. backend/app/adapters/remote_sensing/missing_seedling_adapter.py
2. backend/app/adapters/remote_sensing/growth_monitoring_adapter.py
3. backend/app/adapters/remote_sensing/ndvi_monitoring_adapter.py
4. backend/app/schemas/remote_sensing/ 影像、拼接、算法结果、监测反馈 DTO。
5. backend/app/mappers/remote_sensing/operation_plan_mapper.py
6. backend/app/mappers/remote_sensing/execution_record_mapper.py
7. backend/app/mappers/remote_sensing/evaluation_feedback_mapper.py
8. backend/app/mappers/remote_sensing/prescription_map_mapper.py
9. backend/app/rules/remote_sensing/missing_seedling_review_policy.py
10. backend/app/rules/remote_sensing/growth_monitoring_policy.py
11. backend/app/api/routes/remote_sensing.py，如需要影像上传或结果确认接口。
12. backend/tests/fixtures/remote_sensing/ 缺苗识别、长势监测、穗肥前监测样例。
13. backend/tests/unit/remote_sensing/ 影像结果映射、评价反馈、处方图衔接测试。
14. backend/tests/integration/remote_sensing/ 缺苗到复核、长势监测到施肥处方图链路测试。
```

---

# 10. 前端方向

主要职责：

```text
1. 计划创建页面。
2. 计划详情页面。
3. 农事项日历 / CalendarItem 列表。
4. FarmingTask 列表和详情。
5. OperationPlan 查看。
6. ExecutionRecord 执行反馈录入和查看。
7. Evaluation / Feedback 查看。
8. ReviewRequest 人工复核。
9. 植保补防人工确认页面。
10. 遥感监测结果查看页面。
11. 库存入库和库存列表的最小页面。
```

需要覆盖的页面能力：

| 页面 / 能力 | 说明 |
|---|---|
| 计划创建 | 输入计划基础字段，提交后查看初始化结果 |
| 计划详情 | 展示当前生育期、农事项、任务、反馈和复核 |
| 农事项日历 | 区分 CalendarItem 和 FarmingTask，不把预备农事项当执行入口 |
| 任务详情 | 展示 FarmingTask、OperationPlan、执行状态、历史方案 |
| 作业方案 | 展示不同方向的 parameters、prescriptionMap、operationArea |
| 执行反馈 | 支持人工录入执行结果、附件、异常说明 |
| 评价反馈 | 展示 Evaluation / Feedback，标识是否需要复核 |
| 人工复核 | 处理 approve / reject / adjust / no_action / need_more_info |
| 遥感监测 | 展示缺苗识别、长势监测、异常点位、处方图等结果 |
| 库存 | 药剂 / 肥料入库、库存列表、可用物料查看 |

近期交付物：

```text
1. 页面清单和信息架构。
2. 核心页面原型。
3. 前端 mock 数据。
4. 与 OpenAPI 对齐的接口调用层。
5. OperationPlan 展示组件样例。
6. ExecutionRecord / Feedback 录入组件样例。
7. ReviewRequest 处理页面样例。
8. 第一条垂直闭环的前端演示流程。
```

代码交付物：

```text
1. frontend/src/api/ 基于 OpenAPI 的接口调用层。
2. frontend/src/mocks/ 计划、任务、方案、执行、反馈、复核 mock 数据。
3. frontend/src/pages/plan/ 计划创建和计划详情页面。
4. frontend/src/pages/tasks/ CalendarItem / FarmingTask 列表和任务详情页面。
5. frontend/src/components/operation-plan/ OperationPlan 通用展示组件。
6. frontend/src/components/execution-record/ 执行反馈录入和查看组件。
7. frontend/src/components/evaluation-feedback/ 评价反馈展示组件。
8. frontend/src/pages/review/ ReviewRequest 列表和处理页面。
9. frontend/src/pages/remote-sensing/ 遥感监测结果查看页面。
10. frontend/src/pages/inventory/ 库存入库和库存列表页面。
11. frontend/src/tests/ 或等价测试目录，覆盖第一条垂直闭环页面流程。
```
