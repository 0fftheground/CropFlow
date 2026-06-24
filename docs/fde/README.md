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
```

其中：

```text
1. task-flow-fde-output-template.md 是通用、行业无关的采访输出模板。
2. plant-protection-fde-output-template.md 是基于当前植保实际开发内容整理出的完整参考样例，覆盖杂草和病虫害两条主线。
```
