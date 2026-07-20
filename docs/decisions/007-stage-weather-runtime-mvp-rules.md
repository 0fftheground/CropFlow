# ADR 007：生育期与气象运行期先采用 MVP 规则集

## 决策

当前阶段，生育期与气象运行期先采用一套偏保守、可解释、便于联调的 MVP 规则：

```text
1. 天气来源只区分 observed / forecast / climatology。
2. 同一天气优先级固定为 observed > forecast > climatology。
3. 当前生育期状态只以 observed 和人工录入 raw stage code 为权威输入。
4. forecast 只更新预测层，不直接改变当前已确认阶段。
5. climatology 只作为 forecast 覆盖范围之外的兜底输入。
6. 历史 observed 修正时，不做整季全量回放；按修正日期或最近人工生育期锚点之后重算。
7. WeatherSnapshot 只作为已消费天气留痕、幂等和回刷排查支撑，不扩展成完整气象主数据平台。
8. 第一版前端只暴露“正常 / 预测已刷新 / 待补天气或天气异常”三类天气相关状态。
```

## 背景

P2 收尾到 P3 起步阶段，CropFlow 已经具备真实天气接入、生育期预测刷新、人工录入真实生育期和 WeatherSnapshot 留痕能力，但以下问题如果现在一次性设计过深，会显著拉高实现和联调复杂度：

```text
1. forecast 和 observed 混合回刷时，是否要实时改动任务窗口。
2. 历史天气修正时，是否要支持整季任意版本回放。
3. 气象缓存、审计、回刷和页面提示是否要产品化到完整平台级能力。
4. 当前生育期、预测时间线和前端提示是否要分别暴露不同层次的变化。
```

当前阶段目标是先保证：

```text
1. 生育期当前状态口径稳定。
2. 预测刷新逻辑可解释、可测试。
3. 天气变化不会让 CalendarItem / FarmingTask 无序抖动。
4. 前端和后端有统一的异常提示和运行期留痕。
```

## 结果

### 1. 天气源优先级

同一天的天气输入按以下优先级消费：

```text
observed > forecast > climatology
```

含义：

```text
1. observed 表示过去或当天已确认天气，是当前阶段和积温状态的主要依据。
2. forecast 表示当天及未来预测，只用于刷新预测时间线和未来积温推演。
3. climatology 仅在 forecast 覆盖范围之外用于补齐更远日期的预测窗口。
```

### 2. StageChanged 触发口径

```text
1. 只有 observed 或人工录入真实生育期导致当前阶段实际变化时，才产生 StageChanged。
2. forecast 更新允许刷新 StagePredictionSnapshot / CropThermalTimeState，但默认不产生 StageChanged。
3. climatology 不直接触发当前阶段变化，只服务于更远预测窗口。
```

这样做是为了避免 forecast 小幅波动时反复刷新 CalendarItem / FarmingTask。

### 3. 历史天气修正回刷

当 observed 历史数据被修正时：

```text
1. 默认从被修正日期开始重算，而不是整季全量回放。
2. 如果存在人工录入真实生育期形成的 raw stage code 锚点，则从“修正日期”和“最近锚点日期”两者中更晚的那个日期开始重算。
3. 重算结果写入新的 StagePredictionSnapshot，并更新 CropThermalTimeState。
```

### 4. 人工录入真实生育期的关系

人工录入真实生育期的运行期规则继续保持：

```text
1. 只接受 raw stage code。
2. 第一版允许按联调需要录入未来日期，不再限制只能录入当天或过去日期。
3. 录入后以该 raw stage code 作为锚点，重算后续所有生育期预测日期。
4. 当前阶段编码在人工录入场景下以 raw stage code 为准。
```

因此，气象运行期回刷必须尊重人工锚点，不能直接覆盖已确认的人工阶段起点。

### 5. WeatherSnapshot 的定位

第一版中：

```text
1. WeatherSnapshot 记录 CropFlow 已消费过的单日归一化天气行。
2. 它用于幂等、变化检测、跨计划复用和回刷排查。
3. 它不是完整天气主数据平台，不承担全量历史气象仓职责。
```

### 6. 前端暴露口径

前端第一版不需要完整暴露天气版本链，只需能区分：

```text
1. 正常：当前天气输入和生育期预测链路可用。
2. 预测已刷新：forecast 或 observed 触发了新的预测快照，但当前阶段未必变化。
3. 待补天气 / 天气异常：外部接口失败、天气缺失或无法完成算法所需闭区间数据。
```

## 非目标

当前 ADR 不要求本阶段完成：

```text
1. forecast 驱动的自动任务重排。
2. 任意历史版本的整季天气回放 UI。
3. 完整气象缓存平台、多版本对账面板或复杂审计页面。
4. 跨计划、跨农场的天气统一调度优化。
5. 人工录入真实生育期的额外审核流。
```
