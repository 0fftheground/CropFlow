# 灌溉方向

> 本文档从团队分工总览中拆出，用于单独说明灌溉方向的职责和交付要求。

## 当前阶段说明

当前处于核心对象、ER 图、API contract 仍在收敛的阶段。

因此本方向当前任务以非代码交付为主，用于补齐后续接入契约，而不是立即提交设备回调代码、mapper 或测试代码。

## 当前阶段任务总表

| 方向 | 当前要交什么 | 产出形式 | 依赖谁拍板 |
|---|---|---|---|
| 灌溉 | 灌溉算法接口摘要 | Markdown 摘要 | 核心后端、产品 / 架构负责人 |
| 灌溉 | 灌溉任务类型与流程草案 | 流程说明 / 任务表 | 产品 / 架构负责人 |
| 灌溉 | 方案字段草案 | 字段表 | 核心后端 |
| 灌溉 | 执行与回调字段草案 | 字段表 | 核心后端 |
| 灌溉 | 评价反馈规则草案 | 规则说明 | 产品 / 架构负责人、核心后端 |
| 灌溉 | 设备回调 / 轮询说明 | 协议字段说明 | 核心后端 |
| 灌溉 | 测试场景表 | 场景表 | 无，必要时核心后端确认 |
| 灌溉 | 待决问题清单 | 问题列表 | 产品 / 架构负责人、核心后端 |

## 主要职责

```text
1. 补充灌溉算法接口文档。
2. 明确灌溉任务类型、触发条件和执行流程。
3. 明确灌溉 OperationPlan.parameters。
4. 明确是否需要 operationArea / prescriptionMap。
5. 明确执行模式：人工、设备、第三方系统。
6. 明确设备回调、轮询和人工反馈的数据格式。
7. 定义灌溉 Evaluation / Feedback 规则。
```

## 需要补齐的内容

| 类型 | 需要说明 |
|---|---|
| 任务 | 灌溉任务、排水任务、水层保持、晒田相关任务与计划阶段关系 |
| 算法 | 推荐水量、推荐时间、推荐区域、传感器或气象输入 |
| OperationPlan | 水量、水位目标、执行窗口、田块区域、设备参数、验收标准 |
| 执行 | 人工执行、设备执行、第三方执行的 ExecutionRecord 字段 |
| Evaluation | 实际水位、水层保持结果、执行是否超时、设备是否异常 |
| Feedback | 完成、未完成、异常、需要人工处理、需要重新灌溉或调整计划 |

## 当前阶段非代码任务

```text
1. 灌溉算法接口摘要：
   说明推荐输入、返回结果、执行窗口、失败处理和外部依赖。
2. 灌溉任务类型与流程草案：
   明确灌溉、排水、水层保持、晒田等任务的触发条件和前后依赖。
3. 方案字段草案：
   列出后续灌溉方案至少需要哪些字段，例如水量、水位目标、区域、设备参数、验收标准；不要求现在给最终 OperationPlan JSON。
4. 执行与回调字段草案：
   列出人工执行、设备执行、第三方执行分别需要记录哪些字段。
5. 评价反馈规则草案：
   说明哪些指标表示完成、异常、需复核或需重新灌溉。
6. 设备回调 / 轮询说明：
   明确外部执行状态需要哪些字段，不要求现在定最终 ExecutionRecord 结构。
7. 至少 3 个测试场景：
   - 算法推荐灌溉并生成 OperationPlan。
   - 设备执行成功并生成 Feedback completed。
   - 设备异常或水位不达标并触发 ReviewRequest。
8. 待决问题清单：
   统一列出需要核心后端或产品 / 架构负责人拍板的点。
```

## 当前阶段完成标准

```text
1. 不要求代码提交。
2. 不要求给最终 OperationPlan / ExecutionRecord / Feedback JSON。
3. 需要给出字段草案、流程草案和场景表，供核心后端后续统一实现。
4. 对设备回调和轮询的未知点必须单独列出。
```

## 进入实现阶段后参考的代码落点

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

## 进入实现阶段后代码落点说明

| 交付物 | 最少需要包含 |
|---|---|
| `adapters/irrigation/` | 推荐算法或外部系统调用封装、异常转换、超时处理 |
| `schemas/irrigation/` | 推荐请求响应 DTO、设备回调 DTO、人工反馈 DTO |
| `mappers/irrigation/operation_plan_mapper.py` | 推荐结果到 OperationPlan 的字段映射 |
| `mappers/irrigation/execution_record_mapper.py` | 设备回调或人工反馈到 ExecutionRecord 的映射 |
| `mappers/irrigation/evaluation_feedback_mapper.py` | 执行结果到 Evaluation / Feedback / ReviewRequest 的映射 |
| `rules/irrigation/` | 水位达标、执行异常、是否复核的判断逻辑 |
| `api/routes/irrigation.py` | 水位录入、人工反馈或回调接收接口 |
| `tests/fixtures/irrigation/` | 推荐成功、执行成功、执行异常样例 |
| `tests/unit/irrigation/` | mapper、rule、adapter 的单元测试 |
| `tests/integration/irrigation/` | 推荐到执行反馈、异常到复核的链路测试 |
