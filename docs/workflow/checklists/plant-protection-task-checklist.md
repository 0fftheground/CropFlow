# 植保农事项梳理入口

> 本文档最初是植保方向早期梳理时的粗粒度草稿。  
> 随着杂草防治、病虫害调查/防治、服务评价、人工复核等链路逐步落地，原始清单已经不足以直接支撑后端建模、接口设计和前后端联调。

当前建议：

```text
1. 继续把本目录作为“按农事项查看”的入口。
2. 后续 FDE 采访和业务梳理时，先使用通用模板：
   docs/fde/task-flow-fde-output-template.md
3. 如果是植保方向，再读取植保方向参考文档：
   docs/fde/plant-protection-fde-output-template.md
4. 当单个植保农事项梳理完成后，再把稳定事实回写到：
   - docs/domain/plant-protection.md
   - docs/workflow/task-workflow-matrix.md
   - docs/workflow/flows/
   - docs/api/
```

## 为什么原始清单不够

当前实际开发已经证明，下面这些信息如果采访阶段没有先问清，后面会明显拖慢开发：

```text
1. 这个农事到底是 CalendarItem、TaskIntent、ReviewRequest 还是正式 FarmingTask 的入口。
2. 外部接口到底返回“调查日期”“建议方案”“立即执行结果”还是“条件分支结果”。
3. 哪些字段来自 PlantingPlan / Farm / ExecutionRecord / 天气 / 人工录入。
4. 哪些分支需要人工复核，人工允许做哪些决策。
5. 作业完成后是否继续生成药后调查、补充调查、服务评价等下游事项。
6. 推荐结果变化后，系统是覆盖旧对象、失效旧对象，还是新增一个新对象。
```

## 关联模板

请直接使用：

- [任务 / 流程 FDE 通用输出模板](F:/workspace/CropFlow/docs/fde/task-flow-fde-output-template.md)
- [植保方向 FDE 输出参考](F:/workspace/CropFlow/docs/fde/plant-protection-fde-output-template.md)

## 早期草稿中仍然有价值的几个提醒

```text
1. 土壤封闭、药前调查、茎叶除草、药后调查、补防、服务效果评估确实是杂草主线的核心农事项。
2. “任务触发条件 / 接口依赖 / 系统动作 / 作业流程 / 任务后续操作” 这些维度方向是对的，但颗粒度不够。
3. 以后不要只写“作业流程”，还要把“对象映射、表单字段、人工复核、失败兜底、重算覆盖规则”一起写出来。
```
