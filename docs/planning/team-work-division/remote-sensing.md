# 遥感监测方向

> 本文档从团队分工总览中拆出，用于单独说明遥感监测方向的职责和交付要求。

## 当前阶段说明

当前处于核心对象、ER 图、API contract 仍在收敛的阶段。

因此本方向当前任务以非代码交付为主，用于补齐后续接入契约，而不是立即提交影像处理代码、mapper 或对象样例代码。

## 当前阶段任务总表

| 方向 | 当前要交什么 | 产出形式 | 依赖谁拍板 |
|---|---|---|---|
| 遥感监测 | 遥感算法接口摘要 | Markdown 摘要 | 核心后端、产品 / 架构负责人 |
| 遥感监测 | 任务类型与流程草案 | 任务表 / 流程说明 | 产品 / 架构负责人 |
| 遥感监测 | 方案字段草案 | 字段表 | 核心后端 |
| 遥感监测 | 过程记录字段草案 | 字段表 | 核心后端 |
| 遥感监测 | 评价反馈字段草案 | 字段表 / 规则说明 | 核心后端 |
| 遥感监测 | 下游关系说明 | 关系说明 | 产品 / 架构负责人、核心后端 |
| 遥感监测 | 测试场景表 | 场景表 | 无，必要时核心后端确认 |
| 遥感监测 | 待决问题清单 | 问题列表 | 产品 / 架构负责人、核心后端 |

## 主要职责

```text
1. 明确遥感监测任务类型、触发条件和执行流程。
2. 对接缺苗识别、长势监测、NDVI 长势监测、异常点位识别等算法。
3. 定义遥感监测 OperationPlan.parameters / operationArea / prescriptionMap / acceptanceCriteria。
4. 定义影像上传、影像拼接、算法处理、结果回写的执行记录字段。
5. 明确缺苗识别结果、长势监测结果与后续任务或方案的关系。
6. 定义遥感 Evaluation / Feedback 规则。
7. 明确长势监测与穗肥变量处方图的关系。
```

## 需要补齐的内容

| 类型 | 需要说明 |
|---|---|
| 任务 | 缺苗识别、长势监测、穗肥前长势监测、穗肥后效果抽查、异常点位调查 |
| 算法 | 影像输入、拼接结果、NDVI 结果、缺苗区域、长势等级、异常点位 |
| OperationPlan | 航拍时间、影像类型、监测区域、监测目的、算法参数、验收标准 |
| 执行 | 无人机航测、影像上传、影像拼接、算法处理、结果确认的 ExecutionRecord 字段 |
| Evaluation | 缺苗面积、缺苗严重程度、长势等级变化、异常点位数量、处方图质量 |
| Feedback | 是否完成监测、是否需要补拍、是否需要人工确认、是否触发后续农事或处方生成 |
| 下游关系 | 缺苗识别可触发补苗或复核；穗肥前长势监测可为施穗肥 OperationPlan 提供变量处方图 |

## 当前阶段非代码任务

```text
1. 遥感监测算法接口摘要：
   说明影像输入、拼接依赖、输出结构、异常处理和人工确认点。
2. 任务类型与流程草案：
   明确缺苗识别、长势监测、穗肥前监测、效果抽查、异常点位调查的触发条件和前后依赖。
3. 方案字段草案：
   列出监测任务后续至少需要哪些方案字段，不要求现在给最终 OperationPlan JSON。
4. 过程记录字段草案：
   列出影像上传、拼接、算法处理、结果确认分别需要记录哪些字段。
5. 评价反馈字段草案：
   说明缺苗识别、长势监测、异常点位、处方图质量分别需要哪些评价和反馈字段。
6. 下游关系说明：
   说明缺苗识别、长势监测与补苗、复核、施肥处方图之间的关系。
7. 至少 3 个测试场景：
   - 缺苗识别生成缺苗区域重大事件或复核事项。
   - 常规长势监测生成长势状态更新和异常点位。
   - 穗肥前长势监测生成变量处方图并供施穗肥方案使用。
8. 待决问题清单：
   统一列出需要核心后端或产品 / 架构负责人拍板的点。
```

## 当前阶段完成标准

```text
1. 不要求代码提交。
2. 不要求给最终 OperationPlan / ExecutionRecord / Feedback JSON。
3. 需要给出字段草案、流程草案和下游关系说明，供核心后端后续统一实现。
4. 遥感过程记录必须拆分成多个步骤描述，不能只描述最终结果。
```

## 进入实现阶段后参考的代码落点

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

## 进入实现阶段后代码落点说明

| 交付物 | 最少需要包含 |
|---|---|
| `adapters/remote_sensing/` | 缺苗识别、长势监测、NDVI 等算法调用和结果解析 |
| `schemas/remote_sensing/` | 影像输入、拼接结果、算法结果、反馈 DTO |
| `mappers/remote_sensing/operation_plan_mapper.py` | 监测任务或监测方案到 OperationPlan 的映射 |
| `mappers/remote_sensing/execution_record_mapper.py` | 影像上传、拼接、算法处理过程到 ExecutionRecord 的映射 |
| `mappers/remote_sensing/evaluation_feedback_mapper.py` | 监测结果到 Evaluation / Feedback / ReviewRequest 的映射 |
| `mappers/remote_sensing/prescription_map_mapper.py` | 长势监测结果到 prescriptionMap 的映射 |
| `rules/remote_sensing/` | 缺苗复核、异常点位、是否触发下游动作的判断逻辑 |
| `api/routes/remote_sensing.py` | 影像上传、结果确认或相关查询接口 |
| `tests/fixtures/remote_sensing/` | 缺苗、长势、穗肥前监测样例 |
| `tests/unit/remote_sensing/` | mapper、rule、适配逻辑测试 |
| `tests/integration/remote_sensing/` | 缺苗到复核、长势到施肥处方图链路测试 |
