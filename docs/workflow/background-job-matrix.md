# CropFlow Background Job Matrix

> 本文档只定义 MVP 阶段需要影响数据模型和流程边界的后台任务。  
> 它不是调度平台设计，不展开 cron 表达式、重试策略、分布式锁、Job 日志表或后台配置页面。

---

# 1. 建模原则

```text
1. Background Job Center 负责周期性发现变化，并生成或更新系统对象。
2. 后台任务可以调用算法服务，但不直接绕过 Plan Orchestrator 创建业务闭环。
3. 后台任务可以新建或更新 CalendarItem。
4. 到期生成正式 FarmingTask 仍由 TaskDueCheckJob 触发，并回到 Plan Orchestrator / Task Module。
5. 调查日期推荐不属于调查农事本身，不生成 FarmingTask。
6. 后台任务的执行记录第一版可以进入 EventRecord，不单独建 JobRun 表。
```

---

# 2. 字段说明

| 字段 | 说明 |
|---|---|
| jobKey | 后台任务编码 |
| trigger | 触发时机 |
| algorithmOrService | 调用算法或服务 |
| updatedObjects | 新建或更新的对象 |
| emittedEvents | 产生或记录的事件 |
| idempotencyKey | 建议幂等键 |
| notes | 备注 |

---

# 3. MVP 后台任务矩阵

| jobKey | trigger | algorithmOrService | updatedObjects | emittedEvents | idempotencyKey | notes |
|---|---|---|---|---|---|---|
| DailyWeatherCheckJob | 每日 / 天气数据刷新 | weatherProvider | EventRecord | WeatherUpdated | weatherDate + regionCode + dataVersion | 只负责天气输入变化，不直接生成任务 |
| StagePredictionRefreshJob | WeatherUpdated / PlanKeyInfoChanged / ActualStageRecorded | stagePredictionAlgorithm | CropThermalTimeState / StagePredictionSnapshot / CropStageState | StageChanged / EventRecord | plantingPlanId + inputHash + predictionSource | StagePredictionSnapshot 只追加，不覆盖 |
| AgronomyCalendarRefreshJob | 计划初始化 / StageChanged / PlanKeyInfoChanged / 农事日历版本变化 | agronomyCalendarAlgorithm | CalendarItem | CalendarItemUpdated | plantingPlanId + calendarVersion + inputHash | 生成或更新预备农事项，不生成 FarmingTask |
| SurveyDateRecommendationJob | 每日 / 天气变化 / stage 变化 / 调查窗口变化 | soilTreatmentDiagnosisAlgorithm / diseasePestSurveyDateRecommendationAlgorithm / pestSurveyDateRecommendationAlgorithm | 土壤封闭 / 草害 / 病害 / 虫害调查类 CalendarItem | CalendarItemUpdated | plantingPlanId + workflowKey + stageCode + surveyType + recommendationDate + inputHash | `soil_treatment_diagnosis` 返回土壤封闭推荐日期和茎叶除草药前调查日期；调查日期推荐不属于调查农事流程 |
| TaskDueCheckJob | 定时检查到期窗口 | none | FarmingTask / SystemNotification / EventRecord | TaskDueCheckTriggered / FarmingTaskCreated | plantingPlanId + sourceEntityType + sourceEntityId + checkDate | 到期后生成正式任务 |
| ExecutionStatusPollingJob | 定时兜底轮询外部执行系统 | externalExecutionStatusApi | Execution / ExecutionRecord / DeviceCommand / EventRecord | ExecutionStatusUpdated | externalSystemCode + externalExecutionId + statusVersion | HW 主动回调优先，轮询兜底 |
| DeviceDataSyncJob | 定时同步设备或传感器数据 | deviceDataApi / sensorDataApi | EventRecord | SensorDataUpdated / DeviceDataUpdated | deviceId + dataTime + dataVersion | 第一版只作为输入事件，不直接建业务任务 |

---

# 4. 关键边界

## 4.1 调查日期推荐

```text
SurveyDateRecommendationJob 调用调查日期推荐算法。
算法结果只新建或修改调查类 CalendarItem。
调查 FarmingTask 只在调查日期到期后由 TaskDueCheckJob 生成。
调查 FarmingTask 本身只负责调查执行和调查结果录入。
草害调查和虫害调查的推荐日期都由后台任务维护。
茎叶除草药前调查日期由 soil_treatment_diagnosis 接口返回。
土壤封闭除草 FarmingTask 不调用调查日期推荐算法；但后台任务可以使用 soil_treatment_diagnosis 返回的土壤封闭推荐日期维护土壤封闭 CalendarItem。
```

## 4.2 农事日历刷新

```text
AgronomyCalendarRefreshJob 调用农事日历算法。
它生成的是 CalendarItem，不是 FarmingTask。
如果新预测导致已有 CalendarItem 失效，旧记录标记 invalidated，不物理删除。
```

## 4.3 生育期刷新

```text
StagePredictionRefreshJob 可以因为天气、计划关键字段或实际生育期录入而触发。
它保存 StagePredictionSnapshot，并更新 CropStageState / CropThermalTimeState。
如果当前生育期发生变化，产生 StageChanged。
```

## 4.4 到期任务生成

```text
TaskDueCheckJob 只检查 CalendarItem 是否到达生成窗口。
真正的 FarmingTask 生成仍需要遵守 Plan Orchestrator / Task Module 的边界。
```

---

# 5. 当前不做

```text
1. 不新增 JobRun / JobDefinition / JobSchedule 表。
2. 不做动态 cron 配置后台。
3. 不做通用任务编排引擎。
4. 不做复杂重试、告警和熔断设计。
5. 不把后台任务作为独立业务模块暴露给前端。
```

---

# 6. 对 data-model.md 的影响

```text
1. EventRecord 需要能记录后台任务输入、输出摘要、处理状态和幂等键。
2. CalendarItem 需要支持 updated / invalidated / skipped 等状态。
3. StagePredictionSnapshot 只追加，不覆盖。
4. FarmingTask 生成需要 sourceEntityType + sourceEntityId + idempotencyKey。
5. 暂不需要独立后台任务表。
```
