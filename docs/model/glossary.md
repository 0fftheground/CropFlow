# CropFlow 术语表

## PlantingPlan

种植计划。系统运行的核心上下文，MVP 阶段以单个 PlantingPlan 为编排边界。

## CropStageState

当前生育期状态。PlantingPlan 不重复维护 currentStage，当前生育期以 CropStageState 为准。

## CropThermalTimeState

累计积温状态。用于支撑基于积温阈值字典的生育期预测和阶段判断。

## StagePredictionSnapshot

生育期预测快照。记录每次预测或修正结果，便于追溯和对比。

## CalendarItem

预备农事项。由农事日历接口或规则生成，表示未来可能要做的农事安排，但不是正式任务。

## TaskGenerationService

任务生成服务或函数概念，不是 MVP 第一版核心对象或独立表。它由 TaskDueCheckJob 触发，根据 CalendarItem 的时间窗口和 generationCondition 生成 FarmingTask。

## TaskIntent

任务意图。表示系统认为可能需要生成一个任务，但还需要人工确认、补充信息或保留 NoAction 结果。

## FarmingTask

正式农事任务。是执行闭环入口，可以由 CalendarItem、TaskIntent、ReviewRequest 或人工创建产生。

## OperationPlan

作业方案 / 处方方案。描述具体怎么做，包括作业区域、时间窗口、用量、处方图、设备参数和验收标准。

## Execution

执行实例。表示一次任务执行过程。

## ExecutionRecord

执行结果明细。记录实际执行量、面积、时间、轨迹、图片、完成率等。

## DeviceCommand

设备指令。只在设备执行场景下出现。

## Evaluation

执行评价。用于判断执行结果是否符合 OperationPlan。

## Feedback

反馈。执行评价后的业务反馈结果，不直接生成任务，必须回到 Plan Orchestrator。

## ReviewRequest

人工复核事项。需要人工判断的内容统一进入 ReviewRequest。

## SystemNotification

系统提醒。只负责提醒用户查看或处理事项，不承载核心业务状态。

## InventoryItem

库存物料。用于记录药剂和肥料库存主数据，例如物料类型、名称、规格、批次、当前数量和有效期。

## InventoryTransaction

库存流水。用于记录药剂和肥料的入库、出库或调整。MVP 阶段主要用于药剂入库和肥料入库。

## Plan Orchestrator

计划级总编排器。负责协调 Stage Orchestrator、Runtime Rule Engine、Task Module、Review Module 等模块。

## Stage Orchestrator

生育期编排器。负责生育期预测、真实生育期录入、积温更新和生育期状态变化。

## Runtime Rule Engine

运行期规则引擎。根据运行期事件判断是否生成 TaskIntent，或产生 NeedMoreInfo / NoAction 等规则结果。

NeedMoreInfo / NoAction 不作为独立核心对象，优先作为 TaskIntent 状态或规则判断记录保存。

## Task Module

任务模块。负责 CalendarItem、TaskIntent、FarmingTask、OperationPlan 和任务生命周期相关动作。

## Material & Inventory Module

物料与库存模块。负责 InventoryItem / InventoryTransaction，不直接生成 FarmingTask 或 OperationPlan。

## Execution Module

执行模块。只消费 FarmingTask + OperationPlan，负责 Execution、ExecutionRecord、DeviceCommand 和外部执行系统状态同步。

## Evaluation & Feedback Module

评价与反馈模块。根据 ExecutionRecord 和 OperationPlan 生成 Evaluation / Feedback。Feedback 不能直接生成任务，必须回到 Plan Orchestrator。

## Review Module

人工复核模块。负责 ReviewRequest 和相关 SystemNotification，复核完成后产生 ReviewRequestResolved，并回到 Plan Orchestrator。

## Event Module

事件接入模块。负责接收、标准化和记录 Input Event。

## Background Job Center

后台任务中心。负责定期发现气象、设备、任务到期、执行状态等变化，并生成 Input Event。

## External Execution System

外部执行系统。包括灌溉设备、无人机、第三方作业平台等。既可以接收系统下发，也可以回传执行状态。

## SurveyDateRecommendationJob

调查日期推荐后台任务。用于维护调查类 CalendarItem，不直接生成 FarmingTask。茎叶除草药前调查日期由 `soil_treatment_diagnosis` 接口返回并由后台任务维护。
