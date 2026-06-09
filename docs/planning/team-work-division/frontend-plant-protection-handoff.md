# 种植计划前端联调交接稿

> 本文档用于给前端开发提供“当前已可联调”的页面需求和接口契约。  
> 口径以当前后端代码和已落地 API 为准，不再沿用尚未实现的 `Evaluation`、`SystemNotification` 聚合视图或建议态字段草案。

适用阶段：

```text
P2 - 杂草防治 / 病虫害防治 / 生育期运行期联调
```

接口前缀：

```text
/api
```

接口出入参明细请同时阅读：

```text
docs/api/frontend-plant-protection-api-contract.md
```

---

## 1. 当前前端页面范围

按当前已实现链路，建议前端先按 8 个独立页面规划：

| pageKey | pageName | 目标 | 当前状态 | 说明 |
|---|---|---|---|---|
| `plan_create` | 计划创建 | 创建 `PlantingPlan` | 可直接接真实接口 | 闭环入口 |
| `plan_detail` | 计划详情 | 看计划、任务、复核、生育期和事件总览 | 可直接接真实接口 | 当前可展示生育期状态、积温状态、预测快照和人工录入入口 |
| `calendar_list` | 农事项日历 | 看 `CalendarItem` 列表 | 可后置接入 | 第一版可直接由 `plan_detail` 承载预备农事项列表 |
| `task_detail` | 任务详情 | 看 `FarmingTask`、方案、执行历史 | 可直接接真实接口 | 已有聚合详情接口 |
| `survey_entry` | 调查录入 | 录入杂草 / 病虫害 / 服务评价相关调查结果 | 可直接接真实接口 | 复用 `POST /tasks/{id}/survey-results` |
| `review_request` | 人工复核 | 看审核上下文并提交决策 | 可直接接真实接口 | 已有详情和处理接口 |
| `execution_feedback` | 执行反馈 | 录入正式作业执行结果 | 可直接接真实接口 | 复用 `POST /tasks/{id}/execution-completions` |
| `evaluation_entry` | 服务评价录入 | 录入满意度和联系人 | 可直接接真实接口 | 当前不是独立 `Evaluation` 对象，而是服务评价任务的调查结果录入 |
| `service_effect_survey` | 服务人员现场确认 | 录入现场实际情况和原因 | 可直接接真实接口 | 录入后链路结束 |

---

## 2. 页面流转

```text
plan_create
  -> plan_detail
plan_detail
  -> task_detail (from task card)
  -> review_request (from pending review block)
  -> calendar_list (optional, later)
task_detail
  -> survey_entry
  -> execution_feedback
  -> evaluation_entry
  -> service_effect_survey
survey_entry
  -> task_detail / plan_detail
review_request
  -> plan_detail
execution_feedback
  -> task_detail / plan_detail
evaluation_entry
  -> service_effect_survey / plan_detail
service_effect_survey
  -> plan_detail
```

主链路页面流转建议：

1. `plan_create` 创建计划后跳转 `plan_detail`
2. `plan_detail` 直接分区查看预备农事项、正式任务和待审核事项
3. 第一版不强制接 `calendar_list`，`plan_detail` 直接展示预备农事项即可
4. 后续如需长列表筛选，再把 `calendar_list` 作为可选明细页补上
5. `plan_detail` 的任务卡片进入 `task_detail`
6. `plan_detail` 的待审核区块进入 `review_request`
7. 调查类任务从 `task_detail` 进入 `survey_entry`
8. 正式防治任务从 `task_detail` 进入 `execution_feedback`
9. 服务评价任务从 `task_detail` 进入 `evaluation_entry`
10. 服务评价不满意后，跳转 `service_effect_survey`
11. 各提交页完成后默认返回任务详情或计划详情，具体按返回 id 选择刷新页面

---

## 3. 页面需求

### 3.1 `plan_create`

这个页面只做一件事：创建 `PlantingPlan`。前端需要把基础信息和计划上下文填完整，不要把生育期、任务、复核之类内容塞进创建表单里。

建议展示：

1. 计划名称
2. 农场
3. 地块
4. 稻作类型
5. 种植方式
6. 品种
7. 播种日期
8. 年份和若干可选计划参数

主要操作：

1. 查询稻作类型、种植方式、品种候选项
2. 提交创建
3. 创建成功后进入 `plan_detail`

页面约束：

1. `plan_code` 由后端生成
2. `farm_id` 不建议硬编码，先查农场列表
3. 创建完成后再去补任务和日历信息

### 3.2 `plan_detail`

这是计划的主页面，不只是“详情页”，而是整个计划的总览工作台。它应该同时展示生育期、任务、复核和事件，不需要强制先跳 `calendar_list` 才能看预备农事项。

建议展示成 5 个区块：

1. 计划基础信息
2. 生育期状态
3. 预备农事项
4. 正式任务
5. 待审核事项和事件时间线

每个区块应该展示的内容：

1. 计划基础信息
   计划名称、作物、品种、播种日期、计划状态、农场、地块、年份、关键时间字段

2. 生育期状态
   当前阶段、当前阶段中文名、积温累计值、最后计算日、阈值快照、最新预测时间线

3. 预备农事项
   当前计划下的 `CalendarItem` 列表，重点看标题、建议日期、状态、来源、是否已生成正式任务

4. 正式任务
   当前计划下的 `FarmingTask` 列表，重点看任务类型、状态、计划时间、是否有执行记录

5. 待审核事项和事件时间线
   `ReviewRequest` 列表和 `EventRecord` 列表，方便前端快速判断当前计划是否还卡在审核或事件处理中

主要操作：

1. 进入 `task_detail`
2. 进入 `review_request`
3. 录入真实生育期
4. 展开预备农事项的明细查看
5. 如有权限，进入调试快照

页面约束：

1. 不要把 `CalendarItem`、`FarmingTask`、`ReviewRequest` 混成一个列表
2. 生育期状态不要从前端自己反推，直接读接口
3. `debug-snapshot` 只做开发和排障入口

### 3.3 `calendar_list`

这个页面是 `plan_detail` 的可选明细页，不是强制跳页。列表长、筛选条件多，或者要专门看预备农事项时，再进入这里。

建议展示：

1. 预备农事项标题
2. 建议日期
3. 当前状态
4. 来源任务或来源事件
5. 是否已经生成正式任务

主要操作：

1. 筛选或排序预备农事项
2. 点击事项进入 `task_detail`
3. 返回 `plan_detail`

页面约束：

1. `CalendarItem.generated_task_id` 非空时显示“已生成正式任务”
2. 空值时显示“预备农事项”

### 3.4 `task_detail`

这个页面是任务工作台。不同任务 subtype 不能共用一套页面逻辑，前端至少要拆成调查任务、正式防治任务、服务评价尾链路任务三类。

建议展示的通用区块：

1. 任务主信息
2. 任务来源
3. 任务执行与方案
4. 关联复核
5. 事件记录
6. 下游对象

不同任务类型的侧重点：

1. 调查任务
   适用 subtype：
   `plant_protection.stem_leaf_weed_pre_survey`
   `plant_protection.stem_leaf_weed_recontrol_pre_survey`
   `plant_protection.rice_safety_survey`
   `plant_protection.control_effect_survey`
   `plant_protection.regular_disease_pest_survey`
   `plant_protection.sudden_disease_pest_survey`
   重点看来源 `CalendarItem`、历史调查记录、当前待处理的审核信息

2. 正式防治任务
   适用 subtype：
   `plant_protection.soil_sealing_weed_control`
   `plant_protection.stem_leaf_weed_control`
   `plant_protection.injury_mitigation`
   `plant_protection.disease_pest_control`
   重点看 `operation_plans`、最近执行记录、来源 `TaskIntent`、下游 `CalendarItem`

3. 服务评价尾链路任务
   适用 subtype：
   `plant_protection.service_effect_evaluation`
   `plant_protection.service_effect_survey`
   重点看评价记录、现场确认信息、来源执行记录

主要操作：

1. 调查任务进入 `survey_entry`
2. 正式防治任务进入 `execution_feedback`
3. 服务评价任务进入 `evaluation_entry`
4. 现场确认任务进入 `service_effect_survey`
5. 有审核上下文时查看关联 `review_request`

页面约束：

1. 按 `task_subtype` 决定按钮和表单，不要统一展示所有操作
2. 任务详情里要能看出它是从哪张 `CalendarItem`、`TaskIntent` 或执行记录来的
3. 如果任务已有 `execution_records`，页面应直接展示最近一次执行结果；不要只展示“completed”状态
4. 如果任务已有 `execution_records`，正式作业任务可提供“编辑执行结果”入口，进入对最近一条执行记录的修正流程

### 3.5 `survey_entry`

这个页面是统一的调查录入页，但表单内容必须按 `task_subtype` 切换。杂草调查、病虫害调查、服务评价任务都在这里录入。

建议展示：

1. 任务基础信息
2. 调查说明
3. 动态表单
4. 历史调查结果或关联上下文

当前应覆盖的 subtype：

1. `plant_protection.stem_leaf_weed_pre_survey`
2. `plant_protection.stem_leaf_weed_recontrol_pre_survey`
3. `plant_protection.regular_disease_pest_survey`
4. `plant_protection.sudden_disease_pest_survey`
5. `plant_protection.rice_safety_survey`
6. `plant_protection.control_effect_survey`
7. `plant_protection.service_effect_evaluation`
8. `plant_protection.service_effect_survey`

主要操作：

1. 提交调查结果
2. 提交后刷新任务详情或计划详情

页面约束：

1. 病虫害调查提交后，可能返回 `task_intent_ids` 和 `review_request_ids`
2. 前端不要假设调查只会生成执行记录

病虫调查表单建议：

1. `plant_protection.regular_disease_pest_survey`
   建议固定区先展示：
   `survey_date`、`survey_method`、`bbch_stage`
   其中 `survey_method` 第一版按任务上下文只读回填，不允许用户手改
   `survey_method` 当前只支持 `一级理论防治日期 / 生育期`
   动态区按任务上下文里的调查对象展开；建议优先读取 `source_calendar_item.generation_condition.rawPlan.targets`
   `rawPlan` 中相关字段已统一为英文键：`survey_window`、`targets`、`exclude_reasons`
   `cultivation_type=早稻` 时，任务上下文可能不包含 `DaoFeiShi`
   例如：
   `DaoFeiShi.insects_per_100_hills`
   `DaoWenBing.acute_lesion`
   `DaoWenBing.diseased_leaf_rate`

2. `plant_protection.sudden_disease_pest_survey`
   建议固定区先展示：
   `survey_date`、`bbch_stage`
   动态区同样按调查对象展开，不展示 `survey_method`

3. 病虫调查对象字段建议按“对象卡片”组织，而不是平铺成一个超长表单
4. 前端不要硬编码只支持某一种病虫对象，应允许按任务上下文动态拼 `result_payload`
5. 第一版病虫对象范围直接覆盖完整 5 类：`DaoFeiShi`、`DaoWenBing`、`ErHuaMing`、`DaoZongJuanYeMing`、`WenKuBing`
6. 虽然页面可以按任务上下文突出重点对象，但第一版提交口径建议直接回传完整 5 类对象 schema；非重点对象可折叠显示
7. 若当前页面暂时没有完整病虫 schema，可先支持最小字段提交，再逐步扩展对象卡片

病虫对象卡片字段建议：

| 对象 key | 中文建议 | 字段 | 建议控件 | 取值范围 | 说明 |
|---|---|---|---|---|---|
| `ErHuaMing` | 二化螟 | `dead_sheath_rate` | number input | `0~1` | 枯鞘比例 |
| `ErHuaMing` | 二化螟 | `dead_heart_rate` | number input | `0~1` | 枯心比例 |
| `ErHuaMing` | 二化螟 | `main_larval_instars` | integer input | `0~6` | 主要虫龄；`0` 表示未发现或无主要虫龄 |
| `ErHuaMing` | 二化螟 | `damaged_plant_rate` | number input | `0~1` | 虫伤株比例 |
| `DaoFeiShi` | 稻飞虱 | `insects_per_100_hills` | number input | `>=0` | 每百丛虫量 |
| `DaoWenBing` | 稻瘟病 | `acute_lesion` | boolean switch | `true/false` | 是否发现急性病斑 |
| `DaoWenBing` | 稻瘟病 | `diseased_leaf_rate` | number input | `0~1` | 病叶比例 |
| `WenKuBing` | 纹枯病 | `lesion_on_upper_leaf_sheath` | boolean switch | `true/false` | 倒 2 叶鞘及以上是否发现病斑 |
| `WenKuBing` | 纹枯病 | `diseased_hill_rate` | number input | `0~1` | 病丛比例 |
| `DaoZongJuanYeMing` | 稻纵卷叶螟 | `rolled_leaf_tips_per_100_hills` | number input | `>=0` | 每百丛束尖数 |
| `DaoZongJuanYeMing` | 稻纵卷叶螟 | `larvae_count` | number input | `>=0` | 幼虫数量 |
| `DaoZongJuanYeMing` | 稻纵卷叶螟 | `moths_per_square_meter` | number input | `>=0` | 每平方米蛾量 |

病虫调查表单 schema 草案：

1. `plant_protection.regular_disease_pest_survey`
   固定字段：
   - `survey_date`
     - required: `yes`
     - widget: `date`
     - submit format: `YYYYMMDD`
   - `survey_method`
      - required: `yes`
      - widget: `readonly text / readonly select`
      - allowed values: `一级理论防治日期 / 生育期`
      - source: 任务上下文或 `source_calendar_item.generation_condition.surveyMethod`
   - `bbch_stage`
     - required: `yes`
     - widget: `number`
     - submit type: `int`
   对象卡片：
   - `ErHuaMing`
   - `DaoFeiShi`
   - `DaoWenBing`
   - `WenKuBing`
   - `DaoZongJuanYeMing`
   交互规则：
   - 5 类对象卡片都建议存在；任务上下文里的重点对象默认展开，非重点对象默认折叠
   - 所有 number 字段默认值设为 `0`
   - 所有 boolean 字段默认值设为 `false`
   - `main_larval_instars` 默认值 `0`

2. `plant_protection.sudden_disease_pest_survey`
   固定字段：
   - `survey_date`
     - required: `yes`
     - widget: `date`
     - submit format: `YYYYMMDD`
   - `bbch_stage`
     - required: `yes`
     - widget: `number`
     - submit type: `int`
   对象卡片：
   - `ErHuaMing`
   - `DaoFeiShi`
   - `DaoWenBing`
   - `WenKuBing`
   - `DaoZongJuanYeMing`
   交互规则：
   - 不展示 `survey_method`
   - 5 类对象卡片都建议存在；重点对象默认展开，非重点对象默认折叠
   - 所有 number 字段默认值设为 `0`
   - 所有 boolean 字段默认值设为 `false`
   - `main_larval_instars` 默认值 `0`

推荐前端字段配置骨架：

```json
{
  "task_subtype": "plant_protection.regular_disease_pest_survey",
  "fixed_fields": [
    {
      "key": "survey_date",
      "label": "调查日期",
      "widget": "date",
      "required": true,
      "submit_format": "YYYYMMDD"
    },
    {
      "key": "survey_method",
      "label": "调查方式",
      "widget": "readonly_text",
      "required": true,
      "readonly": true
    },
    {
      "key": "bbch_stage",
      "label": "BBCH阶段",
      "widget": "number",
      "required": true
    }
  ],
  "object_cards": [
    {
      "key": "DaoFeiShi",
      "label": "稻飞虱",
      "collapsed_by_default": false,
      "fields": [
        {
          "key": "insects_per_100_hills",
          "label": "每百丛虫量",
          "widget": "number",
          "default": 0
        }
      ]
    }
  ]
}
```

推荐提交 payload 骨架：

```json
{
  "result_payload": {
    "survey_date": "20260628",
    "survey_method": "一级理论防治日期",
    "bbch_stage": 23,
    "ErHuaMing": {
      "dead_sheath_rate": 0,
      "dead_heart_rate": 0,
      "main_larval_instars": 0,
      "damaged_plant_rate": 0
    },
    "DaoFeiShi": {
      "insects_per_100_hills": 12
    },
    "DaoWenBing": {
      "acute_lesion": false,
      "diseased_leaf_rate": 0
    },
    "WenKuBing": {
      "lesion_on_upper_leaf_sheath": false,
      "diseased_hill_rate": 0
    },
    "DaoZongJuanYeMing": {
      "rolled_leaf_tips_per_100_hills": 0,
      "larvae_count": 0,
      "moths_per_square_meter": 0
    }
  },
  "actual_start_at": "2026-06-28T09:00:00",
  "actual_end_at": "2026-06-28T09:20:00"
}
```

### 3.6 `review_request`

这个页面是审核工作台，不只是查看详情。前端要让审核人看清楚“为什么要审核这件事、审核的是哪份建议、审核通过后会影响什么”。

建议展示：

1. 触发原因
2. 关联计划和任务
3. 候选任务或候选方案
4. 来源调查或来源执行记录
5. 当前待审核状态

主要操作：

1. 查看审核详情
2. 通过审核
3. 拒绝审核
4. 审核完成后回到 `plan_detail`

页面约束：

1. 审核页不要只显示一个按钮，必须能看清上下文
2. 审核结果要能带回任务或方案的 id 变化

### 3.7 `execution_feedback`

这个页面是正式作业的执行回填页，只针对已经生成的正式任务。

建议展示：

1. 任务基础信息
2. 方案信息
3. 当前执行状态
4. 实际执行情况
5. 历史执行记录

主要操作：

1. 录入执行结果
2. 提交后刷新任务详情和计划详情

页面约束：

1. 只用于正式作业任务，不要给调查任务或审核任务开放
2. 提交内容要能够回写执行记录和后续事件

### 3.8 `evaluation_entry`

这个页面是服务评价录入页。它不是独立的 `Evaluation` 对象，而是服务评价任务的调查结果录入。

建议展示：

1. 服务评价任务信息
2. 当前服务对象或执行背景
3. 满意度
4. 评价时间
5. 评价人和联系方式
6. 备注

主要操作：

1. 提交服务评价
2. 根据满意/不满意跳转后续页面

页面约束：

1. 满意则结束
2. 不满意则进入 `service_effect_survey`

### 3.9 `service_effect_survey`

这个页面是服务不满意后的现场确认页，用于记录实际情况和原因。

建议展示：

1. 现场确认任务信息
2. 现场日期
3. 实际情况
4. 原因
5. 备注

主要操作：

1. 提交现场确认结果
2. 返回 `plan_detail`

页面约束：

1. 当前提交后不再自动编排下游对象
2. 这个页面应作为终点表单处理

---

## 4. 页面与接口依赖关系

### 4.1 `plan_create`

| action | method | path | 用途 |
|---|---|---|---|
| 查询稻作类型 | `GET` | `/api/code-dicts?category=culti_type` | 读取稻作类型选项 |
| 查询种植方式 | `GET` | `/api/code-dicts?category=sowingmtd` | 读取种植方式选项 |
| 查询品种 | `GET` | `/api/rice-varieties?query={keyword}&limit=20` | 读取品种选项 |
| 创建计划 | `POST` | `/api/planting-plans` | 创建 `PlantingPlan` |

创建成功后建议前端：

1. 跳转 `plan_detail`
2. 并行读取计划本体、`calendar-items`、`tasks`、`review-requests`

### 4.2 `plan_detail`

| action | method | path | 用途 |
|---|---|---|---|
| 查看计划详情 | `GET` | `/api/planting-plans/{plantingPlanId}` | 读取计划基础信息 |
| 查看当前生育期状态 | `GET` | `/api/planting-plans/{plantingPlanId}/stage-state` | 读取 `CropStageState` |
| 查看积温状态 | `GET` | `/api/planting-plans/{plantingPlanId}/thermal-time-state` | 读取 `CropThermalTimeState` |
| 查看最新生育期预测快照 | `GET` | `/api/planting-plans/{plantingPlanId}/stage-predictions/latest` | 读取 `StagePredictionSnapshot` |
| 人工录入真实生育期 | `POST` | `/api/planting-plans/{plantingPlanId}/actual-stages` | 修正已确认的真实生育期 |
| 查看预备农事项 | `GET` | `/api/planting-plans/{plantingPlanId}/calendar-items` | 读取 `CalendarItem` 列表 |
| 查看正式任务 | `GET` | `/api/planting-plans/{plantingPlanId}/tasks` | 读取 `FarmingTask` 列表 |
| 查看待审核事项 | `GET` | `/api/planting-plans/{plantingPlanId}/review-requests` | 读取 `ReviewRequest` 列表 |
| 查看事件时间线 | `GET` | `/api/planting-plans/{plantingPlanId}/event-records` | 读取 `EventRecord` 时间线 |

建议布局：

1. 顶部显示计划基础字段
2. 单独一个“生育期状态”区块，显示当前阶段、当前阶段中文名、阈值版本、最后计算日
3. 单独一个“积温状态”区块，显示累计积温、当前阈值快照、最后计算日
4. 单独一个“预测时间线”区块，显示 `stage_timeline.stages` 和 `raw_stage_points`
5. 中部显示 `CalendarItem` / `FarmingTask`
6. 侧边或底部显示 `ReviewRequest`
7. 底部显示 `EventRecord`

页面操作建议：

1. 点击 `CalendarItem` 卡片跳转 `calendar_list` 或关联 `task_detail`
2. 点击 `FarmingTask` 卡片跳转 `task_detail`
3. 点击 `ReviewRequest` 卡片跳转 `review_request`
4. 对具备权限的人员开放“人工录入真实生育期”入口，提交 `POST /actual-stages`
5. 人工录入只接受 raw stage code，且日期只能是当天或过去日期
6. 支持同一次提交录入多个 raw stage code；后端会把这些点作为一批人工锚点一起应用
7. 如多条 raw stage 的日期顺序与 raw stage 顺序冲突，后端会直接拒绝录入
8. 提交后后端会以这些 raw stage code 作为锚点重算后续预测日期；锚点之间已存在的中间阶段日期默认保留
9. 如当前阶段变化，后端会刷新受影响的 `CalendarItem / FarmingTask`
10. `debug-snapshot` 可作为开发或排障入口，不作为第一版业务页面必做项

### 4.3 `calendar_list`

| action | method | path | 用途 |
|---|---|---|---|
| 查看预备农事项 | `GET` | `/api/planting-plans/{plantingPlanId}/calendar-items` | 读取 `CalendarItem` 列表 |
| 查看正式任务 | `GET` | `/api/planting-plans/{plantingPlanId}/tasks` | 对照哪些事项已转正式任务 |

前端建议规则：

1. `CalendarItem.generated_task_id` 非空时显示“已生成正式任务”
2. `generated_task_id` 为空时显示“预备农事项”

### 4.4 `task_detail`

| action | method | path | 用途 |
|---|---|---|---|
| 查看任务详情 | `GET` | `/api/tasks/{taskId}` | 聚合读取任务、方案、执行、事件 |

`GET /api/tasks/{taskId}` 当前返回：

```json
{
  "task": {},
  "operation_plans": [],
  "executions": [],
  "execution_records": [],
  "review_request": null,
  "source_task_intent": null,
  "source_calendar_item": null,
  "source_execution_record": null,
  "downstream_calendar_items": [],
  "event_records": []
}
```

补充说明：

1. `source_calendar_item` 当前会带 `generation_condition`
2. 常规病虫调查页建议从 `source_calendar_item.generation_condition.rawPlan` 读取调查窗口和调查对象
3. `rawPlan` 中相关字段使用英文键：`survey_window`、`targets`、`exclude_reasons`

前端建议重点展示：

1. `task`
2. `operation_plans`
3. `execution_records`
4. `review_request`
5. `event_records`

建议按任务类型拆页面区块和按钮，而不是所有任务共用同一套操作：

1. 调查任务
   适用 subtype：
   `plant_protection.stem_leaf_weed_pre_survey`
   `plant_protection.stem_leaf_weed_recontrol_pre_survey`
   `plant_protection.rice_safety_survey`
   `plant_protection.control_effect_survey`
   `plant_protection.regular_disease_pest_survey`
   `plant_protection.sudden_disease_pest_survey`
   必显：任务主信息、来源 `CalendarItem`、历史调查记录、关联复核
   主要操作：进入 `survey_entry`

2. 正式防治任务
   适用 subtype：
   `plant_protection.soil_sealing_weed_control`
   `plant_protection.stem_leaf_weed_control`
   `plant_protection.injury_mitigation`
   `plant_protection.disease_pest_control`
   必显：任务主信息、`operation_plans`、执行记录、来源 `TaskIntent`、下游日历项
   主要操作：进入 `execution_feedback`

3. 服务评价尾链路任务
   适用 subtype：
   `plant_protection.service_effect_evaluation`
   `plant_protection.service_effect_survey`
   必显：任务主信息、来源执行记录、历史评价或调查记录
   主要操作：进入 `evaluation_entry` 或 `service_effect_survey`

### 4.5 `survey_entry`

| action | method | path | 用途 |
|---|---|---|---|
| 查看任务上下文 | `GET` | `/api/tasks/{taskId}` | 读取任务信息和历史 |
| 提交调查结果 | `POST` | `/api/tasks/{taskId}/survey-results` | 录入调查结果 |

通用请求格式：

```json
{
  "result_payload": {},
  "actual_start_at": "2026-05-26T09:00:00",
  "actual_end_at": "2026-05-26T09:30:00"
}
```

通用成功响应格式：

```json
{
  "execution_record_id": 11,
  "event_record_id": 12,
  "farming_task_ids": [],
  "task_intent_ids": [13],
  "review_request_ids": [14]
}
```

字段解释：

1. `farming_task_ids`：提交后直接生成的正式任务
2. `task_intent_ids`：提交后生成的建议态对象
3. `review_request_ids`：提交后生成的待审核事项

### 4.6 `review_request`

| action | method | path | 用途 |
|---|---|---|---|
| 查看复核详情 | `GET` | `/api/review-requests/{reviewRequestId}` | 读取审核上下文 |
| 提交审核结论 | `POST` | `/api/review-requests/{reviewRequestId}/resolve` | 提交复核决策 |

`POST /api/review-requests/{reviewRequestId}/resolve` 请求格式：

```json
{
  "decision": "approve",
  "decision_payload": {},
  "decision_note": "通过",
  "resolved_by": "agronomist_001"
}
```

成功响应格式：

```json
{
  "review_request_id": 21,
  "event_record_id": 31,
  "decision": "approve",
  "status": "resolved",
  "task_intent_ids": [41],
  "farming_task_ids": [51],
  "operation_plan_ids": [61],
  "resolved_at": "2026-05-26T11:00:00"
}
```

### 4.7 `execution_feedback`

| action | method | path | 用途 |
|---|---|---|---|
| 查看任务上下文 | `GET` | `/api/tasks/{taskId}` | 读取任务和当前方案 |
| 提交执行结果 | `POST` | `/api/tasks/{taskId}/execution-completions` | 录入正式作业执行结果 |
| 编辑最近一次执行记录 | `PATCH` | `/api/tasks/{taskId}/execution-records/latest` | 修正最近一次执行结果 |

请求格式：

```json
{
  "operation_date": "2026-04-20T00:00:00",
  "result_payload": {
    "actual": "completed"
  },
  "actual_start_at": "2026-04-20T08:00:00",
  "actual_end_at": "2026-04-20T09:00:00",
  "actual_area": 20.5,
  "actual_amount": 8.0,
  "amount_unit": "kg"
}
```

成功响应格式：

```json
{
  "execution_id": 21,
  "execution_record_id": 22,
  "event_record_id": 23,
  "calendar_item_ids": [24, 25]
}
```

编辑最近一次执行记录请求格式：

```json
{
  "actual_end_at": "2026-05-11T09:30:00",
  "actual_amount": 10.5,
  "result_payload": {
    "note": "corrected"
  }
}
```

编辑成功响应格式：

```json
{
  "execution_id": 21,
  "execution_record_id": 22,
  "event_record_id": 24,
  "updated_fields": [
    "actual_end_at",
    "actual_amount",
    "result_payload",
    "record_time"
  ]
}
```

前端交互建议：

1. 第一次执行反馈仍走 `POST /execution-completions`
2. 任务已有执行记录后，在 `task_detail` 或 `execution_feedback` 提供“编辑执行结果”
3. 编辑只针对最近一条执行记录，不做历史记录列表内逐条编辑
4. 编辑成功后，重新请求 `GET /api/tasks/{taskId}`，刷新执行记录和事件时间线

### 4.8 `evaluation_entry`

| action | method | path | 用途 |
|---|---|---|---|
| 查看任务上下文 | `GET` | `/api/tasks/{taskId}` | 读取服务评价任务上下文 |
| 提交服务评价 | `POST` | `/api/tasks/{taskId}/survey-results` | 录入服务评价结果 |

请求示例：

```json
{
  "result_payload": {
    "is_satisfied": false,
    "evaluated_at": "2026-05-26T10:30:00",
    "evaluator_name": "张三",
    "contact_info": "13800138000",
    "comment": "需要现场复查"
  }
}
```

行为约定：

1. `is_satisfied = true`：链路结束，响应中的 `farming_task_ids` 为空
2. `is_satisfied = false`：直接生成一个 `plant_protection.service_effect_survey` 正式任务，返回其 id 到 `farming_task_ids`

### 4.9 `service_effect_survey`

| action | method | path | 用途 |
|---|---|---|---|
| 查看任务上下文 | `GET` | `/api/tasks/{taskId}` | 读取现场确认任务上下文 |
| 提交现场确认结果 | `POST` | `/api/tasks/{taskId}/survey-results` | 录入现场实际情况和原因 |

请求示例：

```json
{
  "result_payload": {
    "survey_date": "20260501",
    "actual_situation": "现场确认局部杂草残留，未继续扩散。",
    "reason": "前期喷施覆盖不均匀。",
    "comment": "已向农户说明情况。"
  }
}
```

字段校验：

1. `survey_date` 必填
2. `actual_situation` 必填
3. `reason` 必填
4. `comment` 可选

行为约定：

1. 提交后链路结束
2. 当前不会自动生成 `TaskIntent`、`ReviewRequest` 或新的 `FarmingTask`

---

## 5. 页面级字段建议

### 5.1 `plan_create`

必填字段：

1. `plan_name`
2. `farm_id`
3. `field_ids`
4. `culti_type_code`
5. `planting_method_code`
6. `crop_name`
7. `variety_id`
8. `sowing_date`

其中需要特别注意：

1. `plan_code` 由后端生成，前端不传
2. `culti_type_code` 前端展示文案应使用“稻作类型”
3. `planting_method_code` 前端展示文案应使用“种植方式”
4. `variety_id` 前端展示文案应使用“品种”
5. `farm_id` 前端应先通过 `GET /api/farms` 查询候选农场，不建议硬编码

可选字段：

1. `year`
2. `transplant_date`
3. `harvest_date`
4. `transplant_leaf_age`
5. `previous_harvest_date`
6. `ratoon_first_season_harvest_date`
7. `expected_harvest_date`
8. `status`
9. `task_generation_window_days`
10. `metadata`

### 5.2 `plan_detail`

建议至少展示：

1. `PlantingPlan.plan_name`
2. `PlantingPlan.farm_name`
3. `PlantingPlan.crop_name`
4. `PlantingPlan.variety_name`
5. `PlantingPlan.sowing_date`
6. `PlantingPlan.status`
7. `CropStageState.current_stage`
8. `CropStageState.current_stage_name`
9. `CropThermalTimeState.accumulated_thermal_time`
10. `CropThermalTimeState.last_calculated_date`
11. `StagePredictionSnapshot.stage_timeline.stages`
12. `StagePredictionSnapshot.stage_timeline.raw_stage_points`
13. `CalendarItem.title`
14. `CalendarItem.suggested_start_date`
15. `CalendarItem.status`
16. `FarmingTask.title`
17. `FarmingTask.task_subtype`
18. `FarmingTask.status`
19. `ReviewRequest.title`
20. `ReviewRequest.status`
21. `EventRecord.event_type`
22. `EventRecord.processing_status`

### 5.3 `task_detail`

建议至少展示：

1. `task.title`
2. `task.task_subtype`
3. `task.status`
4. `task.planned_start_at`
5. `task.planned_end_at`
6. `task.generation_reason`
7. `operation_plans[].parameters`
8. `operation_plans[].basis`
9. `execution_records[].record_type`
10. `execution_records[].actual_start_at`
11. `execution_records[].actual_end_at`
12. `execution_records[].actual_area`
13. `execution_records[].actual_amount`
14. `execution_records[].amount_unit`
15. `execution_records[].result_payload`
16. `event_records[].event_type`
17. `source_calendar_item`
18. `source_task_intent`
19. `review_request`
20. `downstream_calendar_items`
21. `source_execution_record`

按 subtype 的按钮建议：

1. 调查类任务显示“录入调查结果”
2. 正式作业类任务显示“提交执行反馈”
3. 服务评价任务显示“录入服务评价”
4. 现场确认任务显示“录入现场确认”
5. 若存在 `review_request`，显示“查看审核上下文”
6. 若存在 `execution_records[0]`，正式作业类任务显示“编辑执行结果”

### 5.4 `survey_entry`

当前按任务 subtype 切表单：

1. `plant_protection.stem_leaf_weed_pre_survey`
2. `plant_protection.stem_leaf_weed_recontrol_pre_survey`
3. `plant_protection.regular_disease_pest_survey`
4. `plant_protection.sudden_disease_pest_survey`
5. `plant_protection.rice_safety_survey`
6. `plant_protection.control_effect_survey`
7. `plant_protection.service_effect_evaluation`
8. `plant_protection.service_effect_survey`

前端实现建议：

1. 页面骨架共用
2. 表单 schema 按 `task.task_subtype` 切换
3. 病虫害调查结果提交后，可能返回新的 `task_intent_ids` 和 `review_request_ids`，前端不要假设只会生成执行记录
4. `regular_disease_pest_survey` 建议默认带出 `survey_method`
5. `regular_disease_pest_survey` 的动态对象建议按 `source_calendar_item.generation_condition.rawPlan.targets` 渲染，不要硬编码固定对象集
6. `regular_disease_pest_survey` 和 `sudden_disease_pest_survey` 都建议至少支持：
   `survey_date`
   `bbch_stage`
   一个动态病虫对象字段组
6. 动态病虫对象字段组的 key 直接使用后端 contract 中的对象名，如 `DaoFeiShi`、`DaoWenBing`
7. 第一版若缺少完整中文映射，可先保留对象 code 作为开发态字段名，再补中文展示映射

当前可用病虫对象字段对照表：

| 对象 key | 中文建议 | 当前字段 | 当前来源 |
|---|---|---|---|
| `DaoFeiShi` | 稻飞虱 | `insects_per_100_hills` | 已在后端测试和本地真实联调中使用 |
| `DaoWenBing` | 稻瘟病 | `acute_lesion`、`diseased_leaf_rate` | 已在后端测试和合并防治分支验证中使用 |
| `ErHuaMing` | 二化螟 | `dead_sheath_rate`、`dead_heart_rate`、`main_larval_instars`、`damaged_plant_rate` | 当前按上游算法接口文档预留 |
| `DaoZongJuanYeMing` | 稻纵卷叶螟 | `rolled_leaf_tips_per_100_hills`、`larvae_count`、`moths_per_square_meter` | 当前按上游算法接口文档预留 |
| `WenKuBing` | 纹枯病 | `lesion_on_upper_leaf_sheath`、`diseased_hill_rate` | 当前按上游算法接口文档预留 |

前端组装建议：

1. 第一版建议直接提交完整 5 类对象字段组；页面可按任务上下文突出重点对象，但非重点对象也建议带默认零值一起回传
2. 每个对象字段组都作为 `result_payload` 下的一个子对象，不要拍平成顶层字段
3. `survey_date`、`survey_method`、`bbch_stage` 仍保持在 `result_payload` 顶层
4. 第一版可以先按数字输入框 / 布尔开关实现，不必等待完整农艺字段组件
5. 对于调查结果为未发现或零值的对象，字段组仍应显式回传 `0 / false`，不要省略

### 5.5 `evaluation_entry`

必填字段：

1. `is_satisfied`
2. `evaluated_at`
3. `evaluator_name`
4. `contact_info`

可选字段：

1. `comment`

### 5.6 `service_effect_survey`

必填字段：

1. `survey_date`
2. `actual_situation`
3. `reason`

可选字段：

1. `comment`

---

## 6. 前端联调顺序建议

建议按以下顺序接入，而不是同时起 8 个页面：

1. `plan_create`
2. `plan_detail`
3. `task_detail`
4. `survey_entry`
5. `review_request`
6. `execution_feedback`
7. `evaluation_entry`
8. `service_effect_survey`

原因：

1. 前 6 个页面能先打通杂草防治、病虫害调查和生育期主链路
2. 后 2 个页面是服务评估尾部链路，独立性更强

---

## 7. 当前已知限制

这些点前端需要按“当前后端真实状态”处理：

1. `plan_detail` 当前没有独立 `SystemNotification` 接口
2. `calendar_list` 第一版可以不做，`plan_detail` 已足够承载预备农事项
3. 服务评价当前不是独立 `Evaluation` 对象，而是服务评价任务的调查结果录入
4. `service_effect_survey` 当前录入后链路直接结束
5. 若要演示后台自动把 `CalendarItem` 转为正式调查任务，需要本地启用 scheduler 或使用已有 seed / trace 流程

---

## 8. 给前端的实现建议

1. 所有写接口提交成功后，都优先使用返回的 id 刷新对应详情页，而不是只依赖本地状态推断
2. `survey-results` 返回值要统一处理 `farming_task_ids`、`task_intent_ids`、`review_request_ids`
3. `task_subtype` 应作为页面渲染和表单切换的主分流字段
4. `plan_detail` 第一版至少要包含生育期状态、积温状态和预测时间线，不建议只做任务列表
5. `service_effect_survey` 第一版按终点表单实现，不预埋额外状态机
