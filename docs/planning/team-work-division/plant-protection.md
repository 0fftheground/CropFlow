# 植保方向

> 本文档从团队分工总览中拆出，用于单独说明植保方向的职责和交付要求。

## 当前阶段说明

当前处于核心对象、ER 图、API contract 仍在收敛的阶段。

因此本方向当前任务以非代码交付为主，用于补齐后续接入契约，而不是立即提交 adapter、mapper、API router 或对象样例代码。

## 当前阶段任务总表

| 方向 | 当前要交什么 | 产出形式 | 依赖谁拍板 |
|---|---|---|---|
| 植保 | 各算法接口摘要 | Markdown 摘要 | 核心后端、产品 / 架构负责人 |
| 植保 | 调查录入字段草案 | 字段表 | 核心后端 |
| 植保 | 方案字段草案 | 字段表 | 核心后端、产品 / 架构负责人 |
| 植保 | 执行反馈字段草案 | 字段表 | 核心后端 |
| 植保 | 人工复核规则草案 | 规则说明 / 分支表 | 产品 / 架构负责人 |
| 植保 | 任务流转与分支规则 | 触发规则表 / 分支说明 | 产品 / 架构负责人、核心后端 |
| 植保 | 端到端测试场景 | 场景表 | 无，必要时核心后端确认 |
| 植保 | 待决问题清单 | 问题列表 | 产品 / 架构负责人、核心后端 |

## 主要职责

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

## 当前已确认

```text
1. soil_treatment_diagnosis 返回土壤封闭推荐日期和茎叶除草药前调查日期。
2. weed_treatment_diagnosis 在药前调查结果录入后调用。
3. 病虫防治推荐算法在调查结果录入后调用，不挂在病虫防治作业流程下。
4. /api/get_control_plan 返回最终处方，映射到 OperationPlan.parameters。
5. additional_treatment_diagnosis 返回立即补防时，必须人工确认后才能生成补防任务。
```

## 需要补齐的内容

| 类型 | 需要说明 |
|---|---|
| 任务 | 土壤封闭、茎叶除草药前调查、防治作业、药后调查、补防、病虫调查、防治实施、服务效果评估 |
| 算法 | 每个算法的触发时机、输入来源、输出字段、是否需要人工确认 |
| OperationPlan | 药剂、剂型、厂家、推荐用量、兑水量、作业区域、处方数组、推荐防治日期、方案依据 |
| 执行 | 防治实施的作业前水层、作业过程、作业后水层、执行反馈、附件或轨迹字段 |
| Evaluation | 药害识别、药后调查、服务效果评估、异常点位、评价指标 |
| Feedback | 是否完成、是否异常、是否需要补防、是否需要人工复核、后续任务建议 |

## 当前阶段非代码任务

```text
1. 植保算法接口摘要：
   对 soil_treatment_diagnosis、weed_treatment_diagnosis、after_treatment_diagnosis、additional_treatment_diagnosis、control_plan 分别说明触发时机、输入来源、输出语义、失败处理。
2. 调查录入字段草案：
   明确药前调查、病虫调查、药后调查分别需要记录哪些调查项、附件和人工信息。
3. 方案字段草案：
   列出后续植保方案至少需要哪些字段，例如药剂、用量、作业窗口、依据、风险提示；不要求现在给最终 OperationPlan JSON。
4. 执行反馈字段草案：
   列出植保执行、药后调查、服务效果评估分别需要记录哪些结果字段。
5. 人工复核规则草案：
   明确什么情况下需要复核、复核人需要看到什么上下文、可能做哪些决策。
6. 任务流转与分支规则：
   明确 no_action、重新调查、直接进入方案、进入人工确认等分支。
7. 至少 3 个端到端测试场景：
   - 茎叶除草药前调查后生成防治方案。
   - 药后调查识别异常并触发补防人工确认。
   - 病虫调查结果不需要防治，只记录 NoAction。
8. 待决问题清单：
   统一列出需要核心后端或产品 / 架构负责人拍板的点。
```

## 当前阶段完成标准

```text
1. 不要求代码提交。
2. 不要求给最终 OperationPlan / ExecutionRecord / Feedback / ReviewRequest JSON。
3. 需要给出字段清单、分支规则和场景表，供核心后端后续落到统一对象。
4. 所有需要人工确认或存在歧义的地方都必须显式列出。
```

## 进入实现阶段后参考的代码落点

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

## 进入实现阶段后代码落点说明

| 交付物 | 最少需要包含 |
|---|---|
| `adapters/plant_protection/` | 各算法接口的请求封装、响应解析、异常转换、mock 支持 |
| `schemas/plant_protection/` | 算法请求响应 DTO、调查录入 DTO、内部中间结构 |
| `mappers/plant_protection/operation_plan_mapper.py` | control_plan 或诊断结果到 OperationPlan 的映射 |
| `mappers/plant_protection/evaluation_feedback_mapper.py` | 药后调查、服务效果等结果到 Evaluation / Feedback / ReviewRequest 的映射 |
| `rules/plant_protection/` | 是否生成方案、是否人工确认、是否生成补防意图的判断逻辑 |
| `api/routes/plant_protection.py` | 调查结果录入、必要查询或确认接口 |
| `tests/fixtures/plant_protection/` | 接口请求响应样例、调查样例、异常样例 |
| `tests/unit/plant_protection/` | adapter、mapper、rule 的单元测试 |
| `tests/integration/plant_protection/` | 调查到方案、药后调查到补防复核的链路测试 |
