# CropFlow 团队分工说明

> 本文档用于说明 CropFlow MVP 的通用分工原则、统一提交模板和各方向子文档入口。  
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

## 2.0 当前阶段使用说明

当前项目仍处于核心对象、ER 图、表结构草案和 API contract 收敛阶段。

因此本文件中的 `CalendarItem / TaskIntent / FarmingTask / OperationPlan / ExecutionRecord / Evaluation / Feedback / ReviewRequest` 等名称：

```text
1. 主要用于表达目标语义和后续统一承接对象。
2. 不表示各方向当前就必须提交这些对象的最终 JSON 或代码实现。
3. 在核心对象尚未完成前，各方向可先提交字段草案、关系说明、流程草案、场景表和待决问题清单。
4. 等核心后端完成对象定义后，再把这些材料收敛成统一对象结构和接口。
```

当前阶段给各方向分配任务时，优先要求：

```text
1. 接口摘要。
2. 字段草案。
3. 流程和分支规则说明。
4. 场景表。
5. 待决问题清单。
```

不优先要求：

```text
1. 最终对象 JSON 样例。
2. adapter / mapper / router 代码。
3. 与未落地核心对象强绑定的实现细节。
```

## 2.0.1 关键词说明

以下关键词在本文件中会频繁出现。当前阶段各方向应尽量按这些定义理解和提交材料。

### 核心对象语义

| 关键词 | 当前语义 |
|---|---|
| `PlantingPlan` | 单个种植计划，是当前 MVP 的主上下文对象 |
| `CalendarItem` | 预备农事项，表示建议日期、时间窗口或待到期事项，不是执行入口 |
| `TaskIntent` | 运行期判断后的任务意图或中间决策承接对象，可表达 `no_action`、`need_more_info`、待确认等结果 |
| `FarmingTask` | 正式任务，是执行入口 |
| `OperationPlan` | 具体作业方案或处方方案，承接推荐参数、区域、窗口、依据等内容 |
| `Execution` | 一次执行过程或执行实例 |
| `ExecutionRecord` | 执行过程中的记录，如开始、结束、人工录入、回调、附件、异常等 |
| `Evaluation` | 对执行效果、服务效果、监测结果等做出的评价结果 |
| `Feedback` | 执行或评价后的业务反馈，可能触发复核、补充调查或后续动作 |
| `ReviewRequest` | 人工复核事项，承接需要人工判断的结果 |
| `InventoryItem` | 库存中的物料实体，如药剂、肥料 |
| `InventoryTransaction` | 库存流水，如入库、出库、扣减、调整 |
| `EventRecord` | 外部输入、后台任务输入输出或过程事件的统一记录 |

### 流程和编码关键词

| 关键词 | 当前语义 |
|---|---|
| `workflowKey` | 具体业务流程或农事项流程编码，如 `WF_STEM_LEAF_WEED` |
| `generalFlowKey` | 可复用的通用流程编码，如调查通用流程、防治通用流程 |
| `chainKey` | 跨农事项的链路编码，用于串起多个流程步骤 |
| `taskCategory` | 稳定的大类，如 `plant_protection`、`fertilization` |
| `taskSubtype` | 大类下的具体业务语义，如 `stem_leaf_weed_control` |
| `stageCode` | 生育期阶段编码 |
| `algorithmCode` | 外部算法或内部算法语义编码 |

### 触发和依赖关键词

| 关键词 | 当前语义 |
|---|---|
| `targetType` | 当前规则或表项准备影响的目标对象类型，如 `CalendarItem`、`FarmingTask`、`ReviewRequest` |
| `targetKey` | 当前规则准备作用到的具体流程编码、子类编码或复核类型 |
| `triggerType` | 触发来源的大类，如事件触发、后台任务触发、时间窗口触发、人工触发 |
| `triggerSource` | 具体触发源，如某个事件、某个 job、某个算法结果 |
| `preconditions` | 触发前必须满足的前置条件 |
| `blockingConditions` | 阻断当前动作继续发生的条件 |
| `dependencyType` | 依赖来源的大类，如依赖上游任务、事件、计划、复核或库存 |
| `dependsOn` | 具体依赖对象或依赖结果 |
| `missingDependencyAction` | 依赖缺失时怎么处理 |
| `satisfiedOutput` | 当依赖满足后，预期可产生什么输出 |

### 动作和结果关键词

| 关键词 | 当前语义 |
|---|---|
| `action` | 当前规则命中的动作，如创建、更新、失效、跳过、待确认 |
| `fallbackAction` | 信息不足、调用失败或条件不满足时的兜底动作 |
| `requiresOperationPlan` | 该任务或流程是否必须进入方案生成 |
| `requiresExecution` | 该任务是否进入执行模块 |
| `requiresReview` | 该任务或结果是否存在人工复核入口 |
| `upstreamKeys` | 当前流程依赖的上游流程、链路、job 或关键来源列表 |
| `downstreamKeys` | 当前流程完成后预期会进入的下游流程、链路或结果动作列表 |
| `expectedCreatedObjects` | 测试场景中预期会创建或更新的对象 |
| `expectedNoAction` | 测试场景中不应发生的动作或对象创建 |
| `expectedReview` | 测试场景中是否预期触发人工复核 |

### 当前阶段使用原则

```text
1. 如果某个关键词对应的核心对象还未最终落地，当前先按“目标语义”理解。
2. 各方向当前可以先提交字段草案、关系草案和规则说明，不要求直接给最终对象结构。
3. 如果某个关键词在本方向有特殊含义，应在方向文档里单独补充，不要自行改写通用定义。
```

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

### 2.1.1 `taskCategory / taskSubtype` 的组织规则

各业务方向提交任务定义时，不应只给自然语言描述，必须按统一编码方式提交。

```text
1. taskCategory 表示稳定的大类，只复用系统已存在的大类，不新增同义词。
2. taskSubtype 表示该大类下可执行或可追溯的具体农事项，命名使用 snake_case。
3. 一个 taskSubtype 只表达一个稳定业务语义，不把“触发条件、执行结果、人工决策”编码进名称。
4. 调查、执行、防治、评估、入库、监测等不同语义应拆成不同 taskSubtype。
5. 如流程分为 survey / control / evaluation，优先拆 subtype，不新增核心对象。
6. 新 subtype 先更新 docs/workflow/task-workflow-matrix.md，再进入代码和接口。
```

建议命名方式：

```text
<stage_or_context>_<business_action>
```

示例：

```text
soil_sealing_weed_control
stem_leaf_weed_control
sealing_stage_disease_pest_survey
sealing_stage_disease_pest_control
service_effect_evaluation
```

任务定义提交时，至少提供下表。

| 字段 | 必填 | 说明 |
|---|---|---|
| workflowKey | 是 | 流程唯一编码，如 `WF_STEM_LEAF_WEED` |
| taskCategory | 是 | 任务大类，如 `plant_protection` |
| taskSubtype | 是 | 任务子类，如 `stem_leaf_weed_control` |
| taskName | 是 | 用户可读名称 |
| generalFlowKey | 是 | 复用的通用流程；无则填 `none` |
| stageScope | 否 | 适用生育期或阶段范围 |
| goal | 是 | 该任务要解决什么问题 |
| requiresOperationPlan | 是 | 是否必须生成 `OperationPlan` |
| requiresExecution | 是 | 是否进入 `Execution Module` |
| requiresReview | 是 | 是否存在人工复核入口 |
| upstreamKeys | 否 | 上游 workflowKey / chainKey / jobKey |
| downstreamKeys | 否 | 下游 workflowKey / chainKey / 结果动作 |
| notes | 否 | 约束、例外、待确认点 |

推荐提交格式：

```md
| workflowKey | taskCategory | taskSubtype | taskName | generalFlowKey | stageScope | goal | requiresOperationPlan | requiresExecution | requiresReview | upstreamKeys | downstreamKeys | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| WF_STEM_LEAF_WEED | plant_protection | stem_leaf_weed_control | 茎叶除草 | GENERAL_PLANT_PROTECTION_SURVEY + GENERAL_PLANT_PROTECTION_CONTROL | tillering_before_closure | 草害调查后决定是否实施茎叶除草 | yes | yes | conditional | SurveyDateRecommendationJob | CHAIN_STEM_LEAF_WEED / service_effect_evaluation | 补防结果需人工确认 |
```

### 2.1.2 触发条件和前后依赖的提交格式

业务方向提交“触发条件”和“前后依赖”时，不接受只写一句话。至少用“触发规则表 + 依赖关系表”两张表提交。

当前阶段说明：

```text
如果核心对象尚未落地，targetType 可以继续使用目标对象语义名，
但交付物重点是说明“未来准备落到哪个对象语义上”，不要求现在给最终对象结构。
```

触发规则表：

| 字段 | 说明 |
|---|---|
| targetType | 目标对象：`CalendarItem / TaskIntent / FarmingTask / OperationPlan / ReviewRequest` |
| targetKey | 对应 workflowKey、taskSubtype 或 reviewType |
| triggerType | `event / job / stage / time_window / manual / algorithm_result / execution_result` |
| triggerSource | 触发来源，如 `PlanCreated`、`SurveyDateRecommendationJob`、`weedTreatmentDiagnosisAlgorithm` |
| preconditions | 进入该触发前必须满足的条件 |
| blockingConditions | 阻断条件，如已完成、已失效、缺少上游输入 |
| action | 生成 / 更新 / 失效 / 跳过 / 待确认 |
| idempotencyKeySuggestion | 建议幂等键组成 |
| fallbackAction | 触发失败或信息不足时的兜底动作 |

依赖关系表：

| 字段 | 说明 |
|---|---|
| currentKey | 当前 workflowKey / taskSubtype |
| dependencyType | `upstream_task / upstream_event / upstream_plan / upstream_review / upstream_inventory` |
| dependsOn | 依赖对象 |
| dependencyRule | 依赖规则说明 |
| missingDependencyAction | 依赖缺失时怎么处理 |
| satisfiedOutput | 满足依赖后可产生什么输出 |

推荐提交格式：

```md
#### 触发规则表
| targetType | targetKey | triggerType | triggerSource | preconditions | blockingConditions | action | idempotencyKeySuggestion | fallbackAction |
|---|---|---|---|---|---|---|---|---|
| FarmingTask | stem_leaf_weed_control_survey | job | TaskDueCheckJob | CalendarItem active 且到达生成窗口 | CalendarItem invalidated / 已存在 active task | create | plantingPlanId + calendarItemId + checkDate | 记录 EventRecord 并跳过 |

#### 依赖关系表
| currentKey | dependencyType | dependsOn | dependencyRule | missingDependencyAction | satisfiedOutput |
|---|---|---|---|---|---|
| WF_STEM_LEAF_WEED | upstream_event | soilTreatmentDiagnosisAlgorithm.recommendedSurveyDate | 只有药前调查日期存在时才创建调查 CalendarItem | 标记 need_more_info 或等待下次 job | 调查 CalendarItem |
```

### 2.1.3 算法接口统一提交模板

算法接口必须按统一模板提交，避免各方向只给 URL 或示例 JSON。

```text
1. 每个算法接口至少提供：用途、触发时机、输入来源、请求结构、响应结构、异常结构、字段语义、映射目标、是否需要人工确认。
2. 如果接口文档仍是 docx，也必须补一份 markdown 摘要，便于评审和 agent 消费。
3. 算法输出中所有会进入核心对象的字段，都要注明映射到哪个对象、哪个字段或哪个 JSON 承接字段。
```

推荐模板：

```md
## <algorithmCode>

### 1. 基本信息
- algorithmCode:
- algorithmName:
- purpose:
- owner:
- endpoint:
- method:
- auth:

### 2. 触发时机
- upstream workflowKey / jobKey:
- trigger event:
- trigger step:
- whether sync or async:

### 3. 请求输入
| field | type | required | source | example | notes |
|---|---|---|---|---|---|

### 4. 响应输出
| field | type | meaning | example | targetObject | targetField |
|---|---|---|---|---|---|

### 5. 异常返回
| code | meaning | retryable | fallbackAction | notes |
|---|---|---|---|---|

### 6. 业务语义
- no_action 的判定:
- need_more_info 的判定:
- 是否可直接生成 OperationPlan:
- 是否必须人工确认:

### 7. 样例
- request sample:
- success response sample:
- no_action sample:
- error sample:
```

### 2.1.4 `OperationPlan` 提交模板

业务方向不能只说“会生成方案”，必须明确方案字段如何组织。

当前阶段说明：

```text
如果 OperationPlan 尚未完成统一定义，可先提交“方案字段草案”，
说明后续方案至少需要哪些字段、每个字段的业务含义和来源，
不要求当前就提交最终 OperationPlan JSON。
```

| 字段 | 必填 | 说明 |
|---|---|---|
| planType | 是 | 如 `plant_protection_control`、`fertilization_prescription` |
| algorithmCode | 否 | 方案来源算法 |
| executionMode | 是 | `manual / device / external` |
| operationWindowStart | 否 | 建议开始时间 |
| operationWindowEnd | 否 | 建议结束时间 |
| parameters | 是 | 本方向核心参数，第一版允许 JSON 承接 |
| operationArea | 否 | 区域、地块、分区、GeoJSON 或引用 |
| prescriptionMap | 否 | 变量处方图、区块处方数组 |
| basis | 是 | 方案依据、推荐原因、输入摘要 |
| acceptanceCriteria | 否 | 验收标准 |
| riskNotes | 否 | 风险、限制、人工提示 |

推荐模板：

```json
{
  "planType": "plant_protection_control",
  "algorithmCode": "controlPlanAlgorithm",
  "executionMode": "manual",
  "operationWindowStart": "2026-05-10T06:00:00+08:00",
  "operationWindowEnd": "2026-05-10T18:00:00+08:00",
  "parameters": {},
  "operationArea": {},
  "prescriptionMap": null,
  "basis": {
    "reason": "",
    "sourceEventIds": [],
    "sourceAlgorithm": ""
  },
  "acceptanceCriteria": {},
  "riskNotes": []
}
```

### 2.1.5 `ExecutionRecord / Evaluation / Feedback / ReviewRequest` 提交模板

方向团队要提交的不只是“执行成功/失败”，而是完整闭环字段约定。

当前阶段说明：

```text
如果这些核心对象尚未完成统一定义，可先提交“字段草案 + 分支说明”，
不要求当前就提交最终对象 JSON 或代码结构。
```

执行记录模板：

| 字段 | 说明 |
|---|---|
| recordType | 开始、结束、人工录入、回调、附件上传、异常 |
| actorType / actorId | 人工、设备、第三方系统 |
| actualStartAt / actualEndAt | 实际执行时间 |
| actualArea / actualAmount | 实际面积、药量、水量、肥量等 |
| resultPayload | 本方向实际结果 |
| attachments | 图片、轨迹、报告、影像等 |

评价反馈模板：

| 字段 | 说明 |
|---|---|
| evaluationResult | `pass / warning / fail / unknown` |
| evaluationMetrics | 具体指标，如覆盖率、长势等级、水位偏差 |
| feedbackType | `completed / abnormal / no_action / follow_up_needed / review_needed` |
| feedbackSummary | 一句话摘要 |
| feedbackDetails | 结构化详情 |
| requiresReview | 是否进入人工复核 |
| suggestedNextAction | 建议的后续动作 |

复核模板：

| 字段 | 说明 |
|---|---|
| reviewType | 复核类型 |
| triggerReason | 为什么触发复核 |
| candidateActions | `approve / reject / adjust / no_action / need_more_info` |
| decisionInput | 人工需要看到哪些上下文 |
| resolutionEffect | 决议后影响哪些对象 |

### 2.1.6 测试样例统一提交模板

每个方向至少提交 3 类场景，并使用统一字段描述。

| 字段 | 说明 |
|---|---|
| scenarioId | 场景编号 |
| scenarioName | 场景名称 |
| scope | `unit / integration / e2e` |
| input | 输入计划、事件、算法响应、人工录入 |
| expectedCreatedObjects | 应创建或更新的对象 |
| expectedNoAction | 不应产生的对象或动作 |
| expectedReview | 是否应触发复核 |
| notes | 额外说明 |

推荐模板：

```md
| scenarioId | scenarioName | scope | input | expectedCreatedObjects | expectedNoAction | expectedReview | notes |
|---|---|---|---|---|---|---|---|
| PP-INT-001 | 茎叶除草药前调查后生成防治方案 | integration | 调查 CalendarItem 到期 + 调查结果 + weed_treatment_diagnosis success | TaskIntent / OperationPlan / FarmingTask | 不直接创建补防任务 | no | control_plan 仅在需防治时调用 |
| PP-INT-002 | 药后调查异常触发补防复核 | integration | after_treatment_diagnosis fail + additional_treatment_diagnosis immediate | ReviewRequest | 不直接创建补防 FarmingTask | yes | 需人工确认 |
| PP-INT-003 | 病虫调查结果无需防治 | integration | 调查结果 + diagnosis=no_action | EventRecord / TaskIntent(no_action) | 不创建 OperationPlan / FarmingTask | no | 保留追溯记录 |
```

### 2.1.7 方向交付包最小清单

每个业务方向提交文档时，最少要补齐以下内容。

```text
1. taskCategory / taskSubtype 定义表。
2. 触发规则表和依赖关系表。
3. 算法接口模板文档。
4. 方案字段草案；如核心对象已稳定，可进一步补 OperationPlan JSON 样例。
5. 执行、评价、反馈、复核字段草案；如核心对象已稳定，可进一步补对象样例。
6. 至少 3 个测试场景表。
7. 如涉及后台任务，补 docs/workflow/background-job-matrix.md。
8. 如涉及新流程或新 subtype，补 docs/workflow/task-workflow-matrix.md。
```

### 2.1.8 建议的文档落点

为保证提交物统一，文档建议按下面位置维护。

| 内容 | 建议位置 |
|---|---|
| 任务定义、触发条件、前后依赖 | `docs/workflow/task-workflow-matrix.md` 或 `docs/workflow/flows/` |
| 后台任务相关触发 | `docs/workflow/background-job-matrix.md` |
| 算法接口模板 | `docs/api/` |
| 方向补充说明、字段映射、JSON 样例 | 对应方向章节下补充，必要时新增 `docs/api/<direction>-*.md` |
| 设计取舍 | `docs/decisions/` |

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

# 3. 角色与方向分文档

为避免一个文件同时承载所有方向的职责和交付物，具体分工已拆到以下子文档：

| 类型 | 文档 |
|---|---|
| 产品 / 架构负责人 | `docs/planning/team-work-division/product-architecture-owner.md` |
| 核心后端方向 | `docs/planning/team-work-division/core-backend.md` |
| 农事日历 / 生育期方向 | `docs/planning/team-work-division/calendar-stage.md` |
| 植保方向 | `docs/planning/team-work-division/plant-protection.md` |
| 灌溉方向 | `docs/planning/team-work-division/irrigation.md` |
| 施肥方向 | `docs/planning/team-work-division/fertilization.md` |
| 遥感监测方向 | `docs/planning/team-work-division/remote-sensing.md` |
| 前端方向 | `docs/planning/team-work-division/frontend.md` |

建议使用方式：

```text
1. 先阅读本文件的分工原则、通用职责边界和提交模板。
2. 再进入对应角色 / 方向子文档查看职责、近期交付物和代码交付物。
3. 当新增某一方向的专属规则时，优先更新该方向子文档；如影响通用模板，再回写本文件。
```
