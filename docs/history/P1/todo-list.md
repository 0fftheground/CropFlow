# P1 Todo List

> 目标：收口植保方向 P1 阶段需要冻结的范围、契约、页面和待决事项。  
> 对齐依据：`docs/history/P1/plant-protection-closed-loop-schedule.md`、`docs/domain/plant-protection.md`、`docs/frontend/overview.md`、`docs/domain/calendar-stage.md`。

---

## 1. P1 交付目标

```text
1. 冻结植保范围。
2. 冻结第一条样板链路范围和验收标准。
3. 冻结核心 API contract 和字段草案。
4. 冻结上游链路和关键后台任务最小边界。
5. 冻结前端页面范围、字段缺口和演示路径。
```

---

## 2. 已确认口径

### 2.1 杂草链路与接口契约

- [x] 杂草主线按“一起冻结”口径推进，P1 至少同步冻结以下 workflow 的契约和页面范围：
  `WF_SOIL_SEAL_WEED`、`WF_STEM_LEAF_WEED_SURVEY`、`WF_STEM_LEAF_WEED`、`WF_STEM_LEAF_WEED_POST_SURVEY`、`WF_STEM_LEAF_WEED_ADDITIONAL_CONTROL`、`WF_PLANT_PROTECTION_SERVICE_EVALUATION`。
- [x] `weed_survey_date_diagnosis` 在直播模式下的 `weather_data` 起算日为计划播种日期。
- [x] `soil_treatment_diagnosis` 中 `封闭操作` 表示封闭任务类型名称，系统内部当前固定按 `苗后封闭` 处理。
- [x] 杂草主线不再保留独立 `scheme_info` 概念，统一按“算法请求 payload 组装责任”处理：
  由核心后端 / adapter 负责组装 `PlantingPlan`、`weather_data`、调查结果及算法所需上下文。
- [x] `OperationPlan.parameters` 按杂草防治接口构造最小结构：
  `strategy`、`targetSummary`、`controlTarget`、`recommendedDates`、`weedGerminationDate`、`prescription`、`waterVolumePerMu`、`operationAction`。
- [x] `additional_treatment_diagnosis` 四个结果分支统一沿用返回示例中的字段集合，仅根据不同分支返回不同取值。
- [x] 运行期调查或诊断新形成的防治 / 补防 / 药害缓解建议，先生成 `TaskIntent`，再进入 `ReviewRequest`；审核通过后才创建正式 `FarmingTask`，需要执行方案时再为正式任务创建 `OperationPlan`。

### 2.2 杂草补防分支规则

- [x] `无需补防`：不新增任何新任务，直接进入服务效果评估。
- [x] `需缓解药害`：新增人工 `ReviewRequest`，由人工判断不处理、施肥还是打药。
- [x] `需缓解药害`：如人工复核结果确认需要执行缓解措施，则落正式 `FarmingTask`，并统一使用独立 `taskSubtype=plant_protection.injury_mitigation`。
- [x] `需要待药害缓解后进行补防，补充调查后重新录入数据`：先新增一个药前调查 `CalendarItem`，再按当前时间判断是否直接转成 `FarmingTask`。
- [x] `需要立即补防`：先生成补防 `TaskIntent` 和人工 `ReviewRequest`，复核通过后新增一个 `WF_STEM_LEAF_WEED` 正式 `FarmingTask`，再为该任务创建 `OperationPlan`。
- [x] `无需补防且无需药害缓解`：不新增补防任务，按接口返回的 `service_effect_evaluation_date` 新增服务效果评估 `CalendarItem`。
- [x] `不需要补防但需药害缓解`：新增人工 `ReviewRequest`，并按接口返回的 `additional_survey_date` 新增补充调查 `CalendarItem`。

### 2.3 CalendarItem 与上游触发规则

- [x] 计划创建时调用 `soil_treatment_diagnosis` 和 `weed_survey_date_diagnosis`，分别新增土壤封闭和药前调查两个 `CalendarItem`。
- [x] 播种或移栽日期变更时，触发上述两个 `CalendarItem` 的更新。
- [x] `StageChanged` 当前不影响杂草防治相关任务和 `CalendarItem`。
- [x] 调查类 `CalendarItem` 按推荐日期前 2 周进入 `TaskDueCheckJob` 的正式任务生成窗口。
- [x] `CalendarItem -> FarmingTask` 的主路径按时间窗自动生成，由 `TaskDueCheckJob` 负责，不额外引入特殊生成机制。
- [x] 推荐日期过期后失效；重算结果如有更新则覆盖旧日期。
- [x] 上游链路最小边界收口为：
  `PlantingPlan -> WeatherUpdated -> Stage -> CalendarItem -> TaskDueCheckJob`。

### 2.4 气象数据策略

- [x] `weather_data` 通过第三方接口获取；CropFlow 不额外维护原始气象主数据。
- [x] `DailyWeatherCheckJob` 按天刷新即可；气象获取失败时重试 2 次。
- [x] P1 暂不考虑气象校准规则和补数规则。
- [x] 气象调用留痕只进入 `EventRecord`。
- [x] 如气象或算法调用失败，记录失败事件并提醒用户；不做自动补数。
- [x] “补充调查后新增的药前调查 `CalendarItem` 是否直接转正式任务”按统一窗口规则处理：
  进入推荐日期前 2 周窗口则直接转 `FarmingTask`，否则先保留为 `CalendarItem`。
- [x] 连续逐日 `weather_data` 缺失或算法调用失败时，写入 `SystemNotification`，并在计划详情页暴露“待补气象数据 / 算法调用失败”状态。

### 2.5 服务评价与复核原则

- [x] 服务效果评估字段草案当前最小范围包含：
  `是否满意`、`评价时间`、`评价人`、`联系方式`。
- [x] `ReviewRequest` 的通用触发原则是：
  当运行期算法结果提示需要新增农事、补防或药害缓解建议时，先创建 `TaskIntent`，再创建 `ReviewRequest`；只有审核通过后，编排器才落正式 `FarmingTask`，需要执行方案时再为正式任务创建 `OperationPlan`。

## 3. 待产出项

### 3.1 植保

- [x] 输出 5 个算法摘要：
  `soil_treatment_diagnosis`、`weed_survey_date_diagnosis`、`weed_treatment_diagnosis`、`after_treatment_diagnosis`、`additional_treatment_diagnosis`。
- [x] 整理药前调查字段草案：
  调查项、附件、人工录入信息、必填/可选。
- [x] 整理药后调查字段草案：
  药害等级、防效、异常说明、附件、人工录入信息。
- [x] 整理服务效果评估字段草案：
  在当前最小字段 `是否满意`、`评价时间`、`评价人`、`联系方式` 基础上，补充评价指标、异常点位、结论、是否需要复核。
- [x] 整理 `OperationPlan` 字段草案：
  药剂、剂型、厂家、推荐用量、兑水量、作业区域、推荐日期、方案依据、风险提示。
- [x] 整理执行反馈字段草案：
  是否完成、实际执行时间、异常、附件、轨迹、后续建议。
- [x] 冻结人工复核规则细节：
  触发条件、复核上下文、可执行决策、决策后的系统动作。
- [x] 补至少 3 个端到端场景表：
  药前调查生成方案、药后调查触发补防复核、调查结果 `NoAction`。

### 3.2 核心后端 / 文档同步

- [ ] 将 `docs/api` 中植保 `.docx` 文档沉淀为项目内可引用的 Markdown 契约文档或字段表。
- [ ] 同步更新以下文档中的植保契约描述：
  `docs/model/data-model-validation.md`
  `docs/workflow/task-workflow-matrix.md`
  `docs/workflow/background-job-matrix.md`

### 3.3 前端

- [x] 输出 P1 页面清单和信息架构。
- [x] 输出页面字段缺口表，标记哪些字段当前仍缺后端定义。
- [x] 输出页面与接口依赖关系表。
- [ ] 输出低保真原型，至少覆盖：
  计划详情、农事项/任务列表、调查录入、方案查看、执行反馈、人工复核。
- [x] 输出第一条垂直闭环演示流程。

### 3.4 产品 / 架构负责人

- [x] 冻结第一条样板链路范围：
  第一条样板链路按杂草防治整个环节推进，不只覆盖 `WF_STEM_LEAF_WEED`，还包括土壤封闭、药前调查、药后调查、药害缓解、补防判断和服务效果评估。
- [ ] 冻结 P2 验收标准，避免各方向理解不一致。
- [x] 输出待决事项清单，至少包含：
  `issue`、`owner`、`targetDate`、`currentDecision`、`status`。

当前待决事项清单：

| issue | owner | targetDate | currentDecision | status |
|---|---|---|---|---|
| 固定 `stageCode` 完整枚举值 | 产品 / 架构负责人 | 后续扩展时再处理 | 当前杂草样板链路不阻塞；延后到后续方向接入时统一补齐 | deferred |
| 第一版 `taskSubtype` 建议清单是否继续收敛 | 产品 / 架构负责人 + 核心后端 | P2 过程中按需收口 | 当前先以满足第一条杂草整链路实现为准；`plant_protection.injury_mitigation` 已确认新增 | deferred |
| 第一条样板链路范围是否仍以 `WF_STEM_LEAF_WEED` 为第一优先 | 产品 / 架构负责人 | 已确认 | 第一条样板链路覆盖杂草防治整个环节，不止茎叶除草 | closed |

## 4. 剩余待确认项

- [x] 当前无新的核心业务口径待确认；后续如扩展施肥 / 打药处理方案，再回写人工复核映射规则。

---

## 5. 建议执行顺序

1. 先完成接口摘要和字段表沉淀。
2. 再收口植保字段草案、分支规则和复核规则。
3. 然后收口上游链路和后台任务边界。
4. 最后收口前端页面范围、演示路径和统一待决事项。

---

## 6. 完成判定

P1 可以视为完成，当且仅当以下条件同时满足：

```text
1. 植保范围、样板链路范围、验收标准均已冻结。
2. 植保接口摘要、字段草案、分支规则、复核规则齐备。
3. 上游链路和关键后台任务边界明确，且已同步到核心文档。
4. 前端页面清单、字段缺口、低保真原型和演示流程齐备。
5. 待决事项已有明确责任人和拍板结论。
```
