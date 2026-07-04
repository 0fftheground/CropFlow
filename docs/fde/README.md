# CropFlow FDE Docs

本目录用于保存 FDE 工作方式相关文档。

这里的内容不是系统领域事实，而是“后端开发人员如何采访、梳理、核对并沉淀业务逻辑”的方法文档。

原则：

```text
1. FDE 文档服务于系统与业务人员沟通的策略。
2. 业务事实本身仍应回写到 docs/domain/、docs/workflow/、docs/api/ 等正式文档。
3. 当 FDE 过程产出已稳定为长期系统知识时，应迁出本目录。
```

当前可直接复用的模板：

```text
docs/fde/task-flow-fde-output-template.md
docs/fde/plant-protection-fde-output-template.md
docs/fde/fertilization-fde-draft.md
```

其中：

```text
1. task-flow-fde-output-template.md 是通用、行业无关的采访输出模板。
2. plant-protection-fde-output-template.md 是基于当前植保实际开发内容整理出的完整参考样例，覆盖杂草和病虫害两条主线。
3. fertilization-fde-draft.md 是基于施肥任务清单、workflow 矩阵、方向说明和施肥算法接口整理的施肥方向开发口径参考稿；当前 taskSubtype、处方算法映射和审核上下文以该文档为准。
```

## 推荐产出顺序

施肥等新方向在当前仓库里，建议按下面顺序推进：

```text
1. 先创建 docs/workflow/checklists/ 下的主链路 checklist
2. 再基于 checklist 生成 docs/fde/ 下的 fde-draft
3. 由人工核查 fde-draft，补齐待决点、对象映射、字段和异常分支
4. 已冻结的长期事实再回写 docs/domain/、docs/workflow/、docs/api/，必要时同步 docs/model/
```

补充说明：

```text
1. checklist 是主链路和任务颗粒度入口。
2. fde-draft 是面向开发收口的结构化分析稿，不是最终事实源。
3. docs/domain/ 下的方向文档不是唯一终点；它只承接长期方向知识和阶段性交付要求。
4. workflow、API、data-model 等正式事实仍要分别回到对应目录。
```
