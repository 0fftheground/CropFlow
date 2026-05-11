# 施肥方向

> 本文档从团队分工总览中拆出，用于单独说明施肥方向的职责和交付要求。

## 当前阶段说明

当前处于核心对象、ER 图、API contract 仍在收敛的阶段。

因此本方向当前任务以非代码交付为主，用于补齐后续接入契约，而不是立即提交施肥方案代码、库存扣减代码或对象样例代码。

## 当前阶段任务总表

| 方向 | 当前要交什么 | 产出形式 | 依赖谁拍板 |
|---|---|---|---|
| 施肥 | 施肥算法接口摘要 | Markdown 摘要 | 核心后端、产品 / 架构负责人 |
| 施肥 | 任务类型与阶段关系草案 | 任务表 / 规则说明 | 产品 / 架构负责人 |
| 施肥 | 方案字段草案 | 字段表 | 核心后端 |
| 施肥 | 处方图字段草案 | 字段表 / 结构说明 | 核心后端 |
| 施肥 | 执行反馈字段草案 | 字段表 | 核心后端 |
| 施肥 | 库存关系说明 | 关系说明 / 字段草案 | 核心后端、产品 / 架构负责人 |
| 施肥 | 测试场景表 | 场景表 | 无，必要时核心后端确认 |
| 施肥 | 待决问题清单 | 问题列表 | 产品 / 架构负责人、核心后端 |

## 主要职责

```text
1. 补充施肥算法接口文档。
2. 区分基肥、分蘖肥、穗肥、发苗肥、促芽肥等参数。
3. 明确穗肥前长势监测到变量处方图的关系。
4. 明确是否需要 prescriptionMap。
5. 明确肥料类型、用量、面积、作业窗口和验收标准。
6. 明确施肥作业执行记录、效果抽查和反馈规则。
7. 明确施肥与库存物料的关系。
```

## 需要补齐的内容

| 类型 | 需要说明 |
|---|---|
| 任务 | 基肥、分蘖肥、穗肥、穗肥效果抽查、再生季发苗肥、促芽肥 |
| 算法 | 施肥量、变量处方图、推荐时间、推荐区域、长势监测输入 |
| OperationPlan | 肥料品类、用量、单位、作业区域、处方图、执行窗口、验收标准 |
| 执行 | 作业前水层、施肥作业、作业后水层、农事作业反馈 |
| Evaluation | 穗肥效果抽查、长势变化、处方执行偏差 |
| Feedback | 完成、异常、效果不足、需要复核、是否影响后续农事 |
| 库存 | 肥料库存查询、实际消耗、出库流水 |

## 当前阶段非代码任务

```text
1. 施肥算法接口摘要：
   说明输入字段、推荐输出、异常和 fallbackAction。
2. 任务类型与阶段关系草案：
   明确基肥、分蘖肥、穗肥、发苗肥、促芽肥、效果抽查的触发阶段和前后依赖。
3. 方案字段草案：
   分别列出基肥、分蘖肥、穗肥至少需要哪些方案字段，不要求现在给最终 OperationPlan JSON。
4. 处方图字段草案：
   说明变量处方图需要表达哪些信息，以及与施肥方案的关系。
5. 执行反馈字段草案：
   列出施肥执行、效果抽查、异常反馈至少需要哪些字段。
6. 库存关系说明：
   说明肥料库存、出库、实际消耗之间的业务关系和关键字段，不要求现在落到表结构。
7. 至少 3 个测试场景：
   - 常规施肥生成 OperationPlan 并完成执行反馈。
   - 穗肥前长势监测生成变量处方图。
   - 穗肥效果抽查发现异常并触发 ReviewRequest。
8. 待决问题清单：
   统一列出需要核心后端或产品 / 架构负责人拍板的点。
```

## 当前阶段完成标准

```text
1. 不要求代码提交。
2. 不要求给最终 OperationPlan / prescriptionMap / ExecutionRecord / Feedback JSON。
3. 需要给出字段草案、关系说明和场景表，供核心后端后续统一实现。
4. 施肥参数差异、处方图和库存关系必须显式写清。
```

## 进入实现阶段后参考的代码落点

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

## 进入实现阶段后代码落点说明

| 交付物 | 最少需要包含 |
|---|---|
| `adapters/fertilization/` | 施肥推荐算法调用、变量处方图结果解析、异常处理 |
| `schemas/fertilization/` | 推荐请求响应 DTO、执行反馈 DTO、库存扣减输入结构 |
| `mappers/fertilization/operation_plan_mapper.py` | 推荐结果到 OperationPlan 的映射 |
| `mappers/fertilization/prescription_map_mapper.py` | 外部处方结果到 prescriptionMap 的映射 |
| `mappers/fertilization/execution_record_mapper.py` | 施肥执行结果到 ExecutionRecord 的映射 |
| `mappers/fertilization/evaluation_feedback_mapper.py` | 抽查或反馈结果到 Evaluation / Feedback / ReviewRequest 的映射 |
| `rules/fertilization/` | 库存扣减、效果异常、是否复核的判断逻辑 |
| `api/routes/fertilization.py` | 施肥反馈、抽查录入或相关查询接口 |
| `tests/fixtures/fertilization/` | 基肥、分蘖肥、穗肥、抽查场景样例 |
| `tests/unit/fertilization/` | mapper、rule、库存逻辑测试 |
| `tests/integration/fertilization/` | 处方图到施肥方案、抽查到复核的链路测试 |
