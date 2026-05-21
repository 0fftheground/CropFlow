# CropFlow Team Work Division Entrypoints

本文件用于为 `docs/planning/team-work-division/` 提供二级入口摘要，帮助新 session 按角色或方向定向阅读，而不是逐个打开所有子文档。

## 适用场景

```text
1. 判断某个角色或方向当前该交什么。
2. 判断某个方向现在需要提交非代码材料，还是已经可以进入实现阶段准备。
3. 确认不同方向之间的边界是否清楚，哪些内容必须由核心后端统一收口。
```

## 阅读收益

```text
1. 明确每个角色/方向当前的职责、交付物和完成标准。
2. 避免把总文档里已经拆开的内容重新混在一起读。
3. 避免直接打开超长方向文档时读过头，只读当前任务需要的部分。
```

## 使用建议

```text
1. 先判断当前任务属于“拍板/收口”“核心后端”“业务方向”还是“前端”。
2. 先读本摘要，再只打开对应子文档。
3. 如果任务横跨多个方向，再回到 docs/planning/team-work-division.md 看通用模板和共同约束。
```

## 子文档说明

### `docs/planning/team-work-division/product-architecture-owner.md`

适合场景：

```text
1. 你在做范围冻结、验收标准、规则拍板、跨方向对齐。
2. 你在判断某个问题应该由谁拍板，以及拍板前需要哪些输入。
```

读它能获得：

```text
1. 产品 / 架构负责人当前要收口哪些结论。
2. 当前阶段最关键的拍板职责和完成标准。
```

### `docs/planning/team-work-division/core-backend.md`

适合场景：

```text
1. 你在设计后端对象、表结构、API contract、编排骨架。
2. 你在判断“当前阶段先交文档还是直接开代码”。
```

读它能获得：

```text
1. 核心后端当前应提交的非代码内容。
2. 进入实现阶段后预计要落哪些模块和能力。
3. 哪些事情当前明确不要做。
```

### `docs/planning/team-work-division/calendar-stage.md`

适合场景：

```text
1. 你在处理生育期预测、农事日历、stageCode、CalendarItem 重算。
2. 你在判断 stage 变化会不会影响下游任务。
```

读它能获得：

```text
1. 生育期 / 农事日历方向当前要交哪些接口摘要、规则表和场景表。
2. 当前阶段日历类输出如何承接到统一对象。
```

### `docs/planning/team-work-division/plant-protection.md`

适合场景：

```text
1. 你在处理植保方向，尤其是杂草主线的接口、字段、分支规则和页面依赖。
2. 你需要看当前植保口径是否已经冻结。
```

读它能获得：

```text
1. 植保方向的总职责、统一提交模板和字段草案要求。
2. 杂草主线当前最新接口收口、冻结口径和算法摘要。
3. 植保相关对象如何映射到 TaskIntent / OperationPlan / ReviewRequest。
```

使用提示：

```text
如果只想看当前杂草样板闭环的已确认事项，优先先读 docs/planning/P1/todo-list.md；
只有在需要更细字段草案或完整植保提交模板时，再读本文件。
```

### `docs/planning/team-work-division/irrigation.md`

适合场景：

```text
1. 你在处理灌溉方向的算法、设备执行、回调和轮询问题。
2. 你在判断灌溉方向当前需要补哪些契约，而不是直接写代码。
```

读它能获得：

```text
1. 灌溉方向当前要交哪些接口、字段草案和设备协议说明。
2. 灌溉的执行、评价、反馈和复核需要覆盖哪些点。
```

### `docs/planning/team-work-division/fertilization.md`

适合场景：

```text
1. 你在处理施肥方向、处方图、库存关系和效果抽查。
2. 你在判断施肥方向需要补哪些结构化字段和场景表。
```

读它能获得：

```text
1. 施肥方向当前要交哪些任务定义、处方图说明和库存关系说明。
2. 穗肥前监测与施肥方案衔接需要补哪些材料。
```

### `docs/planning/team-work-division/remote-sensing.md`

适合场景：

```text
1. 你在处理缺苗识别、长势监测、影像处理和下游衔接。
2. 你在判断遥感结果如何进入 Evaluation / Feedback / ReviewRequest。
```

读它能获得：

```text
1. 遥感方向当前要交哪些算法摘要、过程记录字段和下游关系说明。
2. 长势监测与施肥变量处方图衔接当前应如何描述。
```

### `docs/planning/team-work-division/frontend.md`

适合场景：

```text
1. 你在处理页面清单、字段缺口、mock 数据和演示路径。
2. 你在判断前端当前需要哪些非代码交付。
```

读它能获得：

```text
1. 前端当前的页面、组件、字段和接口依赖模板。
2. 杂草 P1 的页面建议稿、字段缺口和演示流程。
```

## 何时回到总文档

在以下情况回读 `docs/planning/team-work-division.md`：

```text
1. 需要统一模板而不是单方向细节。
2. 需要比较多个方向是否使用了相同口径。
3. 需要重新确认跨方向共同约束。
```
