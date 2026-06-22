# ADR 010：药剂和肥料库存使用 InventoryItem / InventoryTransaction 建模

## 决策

药剂和肥料库存不只放在 `EventRecord` 或临时 JSON 中，领域模型上统一使用：

```text
InventoryItem
InventoryTransaction
```

作为正式对象。

## 背景

随着植保和施肥方向扩展，系统需要承接：

```text
1. 物料建档。
2. 入库和出库。
3. 作业消耗。
4. 批次、规格、有效期和数量追溯。
```

如果只把这些信息记在事件里，后续很难稳定支撑库存可用量、消耗追溯和前端展示。

## 结果

当前冻结口径为：

```text
1. InventoryItem 表示药剂或肥料库存主数据。
2. InventoryTransaction 表示每一次入库、出库、消耗或修正流水。
3. Material & Inventory Module 负责这两个对象，不直接生成 FarmingTask 或 OperationPlan。
4. 当前它们仍可在工程实现上 deferred，但对象语义已经冻结，不再回退成纯事件记录。
```
