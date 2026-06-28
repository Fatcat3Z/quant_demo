# 数据与文件重构低风险执行计划

> 状态：Draft for review
> 目标：在不影响当前量化系统运行的前提下，先完成第一批低风险整理。

---

## 1. 执行原则

1. **先文档，后整理**：先让目录治理规则可 review，再动文件
2. **先低风险，后中风险**：优先处理日志、报表、临时脚本，不动主数据与缓存
3. **先新增承接目录，再迁移文件**：避免“搬完了但没有新家”
4. **每一批都可单独回滚**：每次只处理一小类文件
5. **迁移前先确认是否存在代码引用**：即使是看起来像报表文件，也先确认不是脚本输入

---

## 2. 执行边界

### 2.1 本期允许的动作

- 新建治理目录
- 新建 README / 治理文档
- 移动零散日志与人工报告
- 移动明确的临时脚本
- 移动明确的生成报表与图表
- 对目录加说明文档，澄清语义

### 2.2 本期不允许的动作

- 迁移 `stock_trade_demo/stock_data.csv`
- 迁移 `stock_trade_demo/stock_data.parquet`
- 批量重构 `stock_trade_demo/.cache/`
- 迁移 `data/live_trades.csv`
- 修改 `web_app.py`、`choose_stock.py`、`compare_strategies.py` 读取核心数据的路径
- 调整 `strategy/` 为新目录名并修改引用

---

## 3. 建议分阶段执行

## Phase A：建立承接目录与说明文件

### 动作

1. 顶层新建：
   - `reports/`
   - `reports/notes/`
   - `reports/data/`
   - `archive/`

2. `stock_trade_demo/` 新建：
   - `docs/`
   - `reports/`
   - `reports/selection/`
   - `reports/plots/`
   - `reports/probes/`
   - `archive/`
   - `archive/tmp_scripts/`
   - `experiments/`（先建目录，不必立刻迁脚本）

3. 新建说明文件：
   - `strategy/README.md`
   - `stock_trade_demo/reports/README.md`
   - `stock_trade_demo/experiments/README.md`

### 风险评估

- 风险：低
- 原因：只新增目录与说明，不改动运行链路

### 验收点

- 新目录命名清晰
- README 能解释目录语义
- 不影响现有运行

---

## Phase B：迁移低风险文本与记录文件

### 候选对象

- `0523_log.md`
- `0524_gpt.md`
- `0525_gpt.md`
- `0526_todo.md`
- `data_crosscheck_report.md`

### 目标位置

- `reports/notes/`
- `reports/data/`

### 执行动作

1. 迁移前先 grep / 搜索是否存在路径硬编码引用
2. 若仅为人工查看文档，则直接迁移
3. 若存在引用，则先补跳转说明或保留兼容占位文档

### 风险评估

- 风险：低
- 原因：主要是人工阅读文档

### 验收点

- 文件移动后内容不变
- 文档能在新位置被找到
- 无脚本依赖损坏

---

## Phase C：迁移 `stock_trade_demo` 根目录中的临时脚本

### 候选对象

- `stock_trade_demo/tmp_scan_csi1000.py`
- `stock_trade_demo/tmp_verify_timing_changelog.py`

### 目标位置

- `stock_trade_demo/archive/tmp_scripts/`

### 执行动作

1. 先确认最近无主动调用需求
2. 搜索仓库内是否存在引用
3. 若无引用，直接归档
4. 若有引用，先与 PM 确认是否保留原位或加 wrapper

### 风险评估

- 风险：低
- 原因：明显临时性质文件

### 验收点

- 根目录噪声减少
- 无脚本依赖损坏

---

## Phase D：迁移明确的报表产物与图表产物

### 候选对象

- `stock_trade_demo/选股策略详情.csv`
- `stock_trade_demo/选股策略详情_原版策略.csv`
- `stock_trade_demo/选股策略详情_缠论增强.csv`
- `stock_trade_demo/选股策略详情_纯缠论.csv`
- `stock_trade_demo/选股策略详情_Method A.csv`
- `stock_trade_demo/策略对比图表.png`
- `stock_trade_demo/probe_entry_report.md`

### 目标位置

- `stock_trade_demo/reports/selection/`
- `stock_trade_demo/reports/plots/`
- `stock_trade_demo/reports/probes/`

### 执行动作

1. 搜索是否有代码/文档直接引用这些路径
2. 若只是人工查看产物，则迁移
3. 若有脚本显式输出到旧路径，则本轮只迁历史文件，不改脚本；后续单独改脚本输出目录

### 风险评估

- 风险：低到中
- 原因：历史产物通常不是运行输入，但需确认是否被说明文档引用

### 验收点

- 主目录更清晰
- 报表集中到 `reports/`
- 无运行回归

---

## Phase E：只建立规范，不立即迁移实验脚本

### 候选对象

- `final_optimization.py`
- `regime_analysis.py`
- `unused_factors_explore.py`
- `position_sizing_test.py`
- `sell_side_optimize.py`
- `run_overheat_ab_test.py`
- `run_weekly_experiment.py`

### 动作

- 先在 `stock_trade_demo/experiments/README.md` 中登记：
  - 哪些属于实验脚本
  - 哪些属于历史脚本
  - 哪些建议以后迁入 `experiments/`
  - 哪些倾向归档

### 风险评估

- 风险：极低
- 原因：先只建立认知规则，不动物理文件

---

## 4. 每一批执行前的检查清单

### 数据整理专家检查

- 该文件是否为运行输入？
- 该文件是否被脚本硬编码引用？
- 该文件是否为当前主入口依赖？
- 该文件是否只是人工查看产物？
- 迁移后是否需要补 README 或索引？

### 质量验收专家检查

- 迁移是否触碰关键路径？
- 迁移是否影响 README 或文档引用？
- 迁移后是否更清晰，而不是更分散？
- 是否需要保留兼容说明？
- 是否引入新的查找成本？

---

## 5. 回归验证最低标准

即使本期只做低风险整理，也至少要检查：

1. `stock_trade_demo/` 的核心入口文件仍在原位
2. `stock_trade_demo/stock_data.csv` 与 `stock_trade_demo/.cache/` 未被触碰
3. `strategy/` 中 Web 依赖的产物未被迁移
4. `data/live_trades.csv` 未被修改
5. 治理文档与迁移清单与实际结果一致

如后续进入实际运行验证阶段，再追加：

- `GET /api/info`
- `GET /api/factors?strategy=...`
- `GET /api/backtest?strategy=...`
- 首页加载与相关文档/截图核验

---

## 6. 回滚策略

### 文档/日志迁移回滚

- 直接移回原路径
- 恢复引用说明

### 报表迁移回滚

- 将历史产物退回原目录
- 后续再补脚本输出目录治理

### 临时脚本归档回滚

- 若发现仍有使用，移回原位或在原位放 wrapper

### 总原则

- 每批次独立提交、独立验证、独立回滚
- 不做跨多类文件的大批量一次性迁移

---

## 7. 本轮建议执行顺序

### 推荐顺序

1. 先 review 当前三份治理文档
2. 通过后执行 Phase A（仅建目录 + README）
3. 再执行 Phase B（顶层日志/报告）
4. 再执行 Phase C（临时脚本）
5. 再执行 Phase D（报表产物）
6. 最后由质量验收专家做一次回归检查

---

## 8. 本轮完成标准

如果完成以下事项，即可视为第一轮低风险整理准备完成：

- 治理文档定稿
- 迁移映射清单定稿
- 低风险执行计划定稿
- PM review 通过并确认第一批允许动的文件范围
