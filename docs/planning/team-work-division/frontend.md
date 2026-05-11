# 前端方向

> 本文档从团队分工总览中拆出，用于单独说明前端方向的职责和交付要求。

## 当前阶段说明

当前处于核心对象、ER 图、API contract 仍在收敛的阶段。

因此本方向当前任务以非代码交付为主，用于补齐页面信息架构和字段需求，而不是立即交付正式页面代码。

## 当前阶段任务总表

| 方向 | 当前要交什么 | 产出形式 | 依赖谁拍板 |
|---|---|---|---|
| 前端 | 页面清单和信息架构 | 页面表 / 信息架构图 | 产品 / 架构负责人 |
| 前端 | 核心页面低保真原型 | 原型图 / 线框图 | 产品 / 架构负责人 |
| 前端 | 页面字段需求清单 | 字段表 | 核心后端 |
| 前端 | mock 数据需求说明 | 需求说明 | 核心后端 |
| 前端 | 页面与接口依赖关系表 | 对照表 | 核心后端 |
| 前端 | 关键组件说明 | 组件说明 | 产品 / 架构负责人、核心后端 |
| 前端 | 第一条闭环演示流程 | 页面流转说明 | 产品 / 架构负责人 |
| 前端 | 待决问题清单 | 问题列表 | 产品 / 架构负责人、核心后端 |

## 主要职责

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

## 需要覆盖的页面能力

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

## 当前阶段非代码任务

```text
1. 页面清单和信息架构。
2. 核心页面低保真原型。
3. 页面字段需求清单。
4. mock 数据需求说明。
5. 页面与接口依赖关系表。
6. 关键组件说明：
   包括方案展示、执行反馈录入、复核处理 3 类组件要展示或录入什么信息。
7. 第一条垂直闭环的前端演示流程。
8. 待决问题清单：
   统一列出需要核心后端或产品 / 架构负责人拍板的点。
```

## 当前阶段完成标准

```text
1. 页面清单和信息架构：
   需要明确页面名称、入口、主要对象、依赖接口和页面间跳转关系。
2. 核心页面低保真原型：
   至少覆盖计划创建、计划详情、任务详情、执行反馈、复核处理页面。
3. 页面字段需求清单：
   需要按页面列出需要展示和录入的字段，并标记哪些字段当前还缺后端定义。
4. mock 数据需求说明：
   说明前端后续需要哪些 mock 结构，不要求现在给最终对象 mock。
5. 页面与接口依赖关系表：
   需要明确每个页面依赖哪些接口、哪些接口目前还不存在。
6. 关键组件说明：
   需要说明方案展示、执行反馈录入、复核处理组件各自的输入输出信息。
7. 第一条垂直闭环的前端演示流程：
   需要给出从计划创建到任务查看、反馈录入、复核处理的页面流转。
8. 不要求当前提交正式页面代码或最终 mock 数据。
```

## 进入实现阶段后参考的代码落点

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

## 进入实现阶段后代码落点说明

| 交付物 | 最少需要包含 |
|---|---|
| `frontend/src/api/` | 接口调用封装、请求响应类型、错误占位和 mock 切换方式 |
| `frontend/src/mocks/` | 计划、任务、方案、执行、反馈、复核的 mock 数据样例 |
| `frontend/src/pages/plan/` | 计划创建和计划详情页面 |
| `frontend/src/pages/tasks/` | CalendarItem / FarmingTask 列表和任务详情页面 |
| `frontend/src/components/operation-plan/` | 方案参数、区域、处方图、依据展示组件 |
| `frontend/src/components/execution-record/` | 执行反馈录入和查看组件 |
| `frontend/src/components/evaluation-feedback/` | 评价反馈展示组件 |
| `frontend/src/pages/review/` | ReviewRequest 列表和处理页面 |
| `frontend/src/pages/remote-sensing/` | 遥感结果查看页面 |
| `frontend/src/pages/inventory/` | 药剂 / 肥料库存相关最小页面 |
| `frontend/src/tests/` | 第一条闭环页面流转或关键组件测试 |
