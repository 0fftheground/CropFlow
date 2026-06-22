# FDE 农事项接入访谈与文档沉淀指南

> 本文档面向 Forward Deployed Engineer。  
> 你负责向施肥、灌溉、遥感监测、农事日历 / 生育期等方向同事获取关键业务和接口信息，再整理成 CropFlow 可以开发、评审和联调的项目文档。  
> 方向同事不需要直接按本文档完整交付；他们只需要回答问题、提供原始资料、确认你整理后的结论。
> 通用 FDE 工作流程见 `docs/fde/fde-standard-workflow.md`；本文档是农事项接入场景下的专项模板。

---

## 1. FDE 的目标

FDE 的任务不是转发资料，而是把各方向的业务知识翻译成系统可落地的接入材料。

```text
1. 从业务同事那里获取农事项、算法、规则、接口、异常和人工判断逻辑。
2. 判断这些信息是否足以让核心后端拆解对象、workflow、job 和接口。
3. 把原始资料整理成统一项目文档，而不是让每个方向各写一套格式。
4. 标出缺口、风险和待拍板问题，推动对应 owner 确认。
5. 在后端接口稳定后，再协助沉淀前端 API contract 和 handoff。
```

## 2. 工作边界

FDE 应该做：

```text
1. 组织访谈和资料收集。
2. 用 CropFlow 的统一对象语言重写业务说明。
3. 把不确定点显式标为 TBD 或待决问题。
4. 维护方向总纲、任务清单、接口摘要、映射说明、场景表。
5. 推动产品 / 架构负责人、核心后端、算法同事、前端同事逐步确认。
```

FDE 不应该做：

```text
1. 在信息不足时替业务同事拍板农艺规则。
2. 在 FastAPI 接口尚未收敛前伪造前端 API contract。
3. 直接照搬厂商文档，不解释系统何时调用、如何分支、落到哪个对象。
4. 为了文档完整性虚构字段、状态或异常码。
5. 让方向同事承担 CropFlow 内部对象建模工作。
```

## 3. 分阶段产物

### 3.1 P0：访谈后即可沉淀

P0 的目标是判断这个方向能不能进入后端拆解。此阶段不要求最终接口、最终英文字段或前端 API contract。

| 产物 | 建议落点 | FDE 要做什么 |
|---|---|---|
| 方向总纲 | `docs/domain/<direction>.md` | 整理范围、任务类型、职责边界、冻结口径、待决问题 |
| 主链路任务清单 | `docs/workflow/checklists/<direction>-task-checklist.md` | 按一个个农事项拆清触发、依赖、动作、分支和后续 |
| 外部接口资料摘要 | `docs/api/<direction>_<capability>_api.md` | 把算法、数据源、设备接口的已知输入输出和缺口转成 markdown |
| 场景表 | 方向总纲或任务清单 | 至少整理正常、无需动作、异常或需复核三类场景 |
| 待决问题清单 | 方向总纲或任务清单 | 记录问题、影响、owner、建议确认顺序 |

### 3.2 P1：后端拆解前补齐

P1 的目标是让核心后端可以开始对象、service、job、adapter 和测试拆解。

| 产物 | 建议落点 | 触发条件 |
|---|---|---|
| 入参组装和返回映射说明 | `docs/api/<direction>_payload_mapping.md` | 外部接口字段基本明确后 |
| workflow 矩阵更新 | `docs/workflow/task-workflow-matrix.md` | `workflowKey / taskSubtype` 基本冻结后 |
| background job 矩阵更新 | `docs/workflow/background-job-matrix.md` | 存在定时推荐、到期检查、轮询或同步任务时 |
| 数据模型影响说明 | `docs/model/data-model.md` 或方向文档章节 | 涉及新增字段、JSON、库存、执行记录、评价反馈时 |

### 3.3 P2：前端联调前补齐

P2 的目标是让前端可以稳定开发页面和交互。

| 产物 | 建议落点 | 触发条件 |
|---|---|---|
| 前端 API contract | `docs/api/frontend-<direction>-api-contract.md` | FastAPI 路由、请求响应、状态枚举基本稳定后 |
| 前端 handoff | `docs/frontend/<direction>-handoff.md` | 页面流程、操作入口和 mock 场景明确后 |
| 前端 mock 场景 | contract 或 handoff | 需要前端并行开发或演示时 |

## 4. 访谈顺序

不要从“接口字段有哪些”开始问。更稳的顺序是：

```text
1. 先问业务链路：这个方向到底有哪些农事项。
2. 再问触发条件：什么时候应该出现这些农事项。
3. 再问判断规则：什么情况下做、什么情况下不做、什么情况下需要人工确认。
4. 再问外部接口：算法、数据源、设备系统提供哪些输入输出。
5. 再问执行闭环：任务生成后谁执行、怎么回传、如何评价、是否复核。
6. 最后问前端展示：用户需要看到什么、能操作什么、哪些状态最重要。
```

原因：

```text
如果先问接口字段，通常只能得到厂商 API 或算法参数，但仍然不知道系统什么时候调用、调用后创建什么对象、失败时怎么兜底、前端为什么要展示这些字段。
```

## 5. 访谈问题清单

### 5.1 范围和任务

| 问题 | 你要判断什么 |
|---|---|
| 这个方向本阶段必须接入哪些农事项？ | 形成 taskSubtype 草案 |
| 哪些农事项只是未来能力，不进入当前阶段？ | 写入不覆盖范围 |
| 每个农事项解决什么业务问题？ | 判断是否需要独立 workflow |
| 这些农事项是否有固定生育期、日期窗口或天气条件？ | 判断是否依赖 stage / weather / job |
| 有没有上下游顺序？ | 判断 chainKey 或 upstreamKeys / downstreamKeys |

### 5.2 触发和分支

| 问题 | 你要判断什么 |
|---|---|
| 什么情况下生成预备农事项？ | 是否创建 CalendarItem |
| 什么情况下生成正式任务？ | 是否创建 FarmingTask |
| 什么情况下只记录建议但不执行？ | no_action 分支 |
| 什么情况下信息不足？ | need_more_info 分支 |
| 什么情况下需要人工确认？ | ReviewRequest 入口 |
| 同一个任务重复触发时怎么办？ | 幂等和阻断条件 |

### 5.3 外部接口和数据

| 问题 | 你要判断什么 |
|---|---|
| 这个农事项依赖哪些算法、传感器、设备或第三方系统？ | 外部接口清单 |
| 接口由谁负责？是否已有文档、样例或环境？ | owner 和资料来源 |
| 请求字段从哪里来？ | 入参组装来源 |
| 返回字段分别代表什么业务含义？ | 响应语义 |
| 返回什么表示无需动作、建议执行、异常或失败？ | 业务分支 |
| 接口失败、超时或字段缺失时怎么办？ | fallbackAction |

### 5.4 作业方案和执行

| 问题 | 你要判断什么 |
|---|---|
| 需要生成具体作业方案吗？ | 是否需要 OperationPlan |
| 方案必须包含哪些参数？ | OperationPlan.parameters |
| 是否涉及区域、处方图、设备参数或物料？ | operationArea / prescriptionMap / inventory |
| 谁执行任务？人工、设备、第三方系统还是只记录？ | executionMode |
| 执行结果如何回传？ | ExecutionRecord 字段 |
| 执行失败、部分完成或取消时怎么办？ | 异常反馈和复核 |

### 5.5 评价、反馈和后续动作

| 问题 | 你要判断什么 |
|---|---|
| 执行后是否需要效果评价？ | Evaluation |
| 评价指标是什么？ | Evaluation.metrics |
| 反馈会不会触发后续任务？ | Feedback 回到 Plan Orchestrator |
| 什么情况下结束链路？ | completed 条件 |
| 什么情况下补充调查、再次执行或人工复核？ | downstreamKeys / ReviewRequest |

### 5.6 前端展示

P0 阶段只问业务展示，不问最终接口。

| 问题 | 你要判断什么 |
|---|---|
| 用户需要看到哪些关键信息？ | 页面字段草案 |
| 用户需要做哪些操作？ | 操作入口 |
| 哪些状态必须明显展示？ | 状态枚举候选 |
| 需要哪些演示场景？ | mock 场景 |
| 哪些字段来自后端任务，哪些来自算法或执行反馈？ | 后续 frontend contract 输入 |

## 6. 文档写法

### 6.1 方向总纲

建议结构：

```md
# <方向名>方向

## 当前范围
- 本阶段覆盖：
- 本阶段不覆盖：
- 主要 owner：

## 任务类型草案
| workflowKey | taskCategory | taskSubtype | taskName | stageScope | goal | requiresOperationPlan | requiresExecution | requiresReview | notes |
|---|---|---|---|---|---|---|---|---|---|

## 冻结口径

## 待决问题
| questionId | question | impact | owner | status | notes |
|---|---|---|---|---|---|
```

### 6.2 主链路任务清单

每个任务按同一结构写，便于后端拆解：

```md
## <任务名称>

- 业务目的:
- 触发条件:
- 上游依赖:
- 接口依赖:
- 系统动作:
- no_action 条件:
- need_more_info 条件:
- need_review 条件:
- OperationPlan 字段草案:
- Execution / Feedback 字段草案:
- 后续动作:
- 待决问题:
```

### 6.3 外部接口资料摘要

P0 允许写草案和缺口：

```md
## <接口或算法名称>

### 已知信息
- owner:
- endpoint: TBD
- method: TBD
- 使用时机:

### 请求输入草案
| field | type | required | source | unit | knownOrTbd | notes |
|---|---|---|---|---|---|---|

### 响应输出草案
| field | type | meaning | unit | example | branchMeaning | knownOrTbd |
|---|---|---|---|---|---|---|

### 缺口
| gap | impact | owner | nextAction |
|---|---|---|---|
```

### 6.4 入参组装和返回映射

P1 再补：

```md
## 请求入参组装
| requestField | sourceObject | sourceField | transformRule | missingAction | notes |
|---|---|---|---|---|---|

## 返回结果映射
| responseField | meaning | targetObject | targetField | transformRule | notes |
|---|---|---|---|---|---|

## 分支到系统动作
| condition | systemAction | createdOrUpdatedObjects | noAction | reviewRequired | notes |
|---|---|---|---|---|---|
```

### 6.5 场景表

```md
| scenarioId | scenarioName | input | expectedCreatedObjects | expectedNoAction | expectedReview | openQuestions |
|---|---|---|---|---|---|---|
| <DIR>-001 | 正常主链路 |  |  |  | no |  |
| <DIR>-002 | 无需动作 |  |  |  | no |  |
| <DIR>-003 | 异常或需复核 |  |  |  | yes |  |
```

## 7. 信息是否足够的判断标准

### 7.1 P0 足够

```text
1. 能列出本方向本阶段的主要 taskSubtype。
2. 每个 taskSubtype 都有触发条件、上游依赖和下游动作草案。
3. 已知外部接口、算法或数据源的 owner 和资料来源。
4. 正常、无需动作、异常或需复核三类场景能讲通。
5. 待决问题已经显式列出，而不是藏在正文里。
```

### 7.2 P1 足够

```text
1. 外部接口字段基本明确。
2. 入参来源和返回映射能落到核心对象或明确 JSON 承接字段。
3. workflowKey / taskSubtype 基本冻结。
4. 后台 job、库存、执行记录、评价反馈、复核入口的影响已经说明。
```

### 7.3 P2 足够

```text
1. 后端 FastAPI 路由、请求响应和状态枚举基本稳定。
2. 前端页面字段和操作入口明确。
3. 前端 mock 覆盖正常、无需动作、异常或需复核场景。
```

## 8. FDE 需要特别追问的风险点

```text
1. 业务同事说“看情况处理”时，要追问具体判断条件。
2. 业务同事说“人工确认”时，要追问确认什么、谁确认、确认后系统做什么。
3. 业务同事说“接口会返回建议”时，要追问建议字段、单位、置信度、无建议和失败的区别。
4. 业务同事说“执行完成”时，要追问完成标准、失败标准、部分完成和异常反馈。
5. 业务同事给中文字段时，要追问稳定英文 key 是否已有；没有则先标 TBD，不要自造为冻结字段。
6. 业务同事给页面需求时，要追问字段来源，不要直接推导后端 contract。
```

## 9. 评审和确认节奏

```text
1. FDE 完成 P0 草案后，请方向同事确认业务事实和缺口。
2. P0 草案确认后，请产品 / 架构负责人确认范围、对象边界和冻结口径。
3. P1 文档完成后，请核心后端确认 workflow、job、对象映射和幂等。
4. FastAPI 草案稳定后，再请前端确认 API contract、页面字段和 mock 场景。
5. 每次评审只确认当前阶段能确认的内容，不把 P2 问题提前伪装成 P0 结论。
```

## 10. 常见错误

```text
1. 把方向同事提供的原始资料直接放进项目文档，没有翻译成系统对象语言。
2. 为了让文档看起来完整，把 TBD 写成已确认结论。
3. 在后端接口未稳定前编写 frontend API contract。
4. 只记录“需要复核”，没有写复核触发条件和复核后动作。
5. 只写算法输入输出，没有写系统什么时候调用和失败如何兜底。
6. 只写正常链路，没有 no_action、need_more_info、异常或需复核场景。
```
