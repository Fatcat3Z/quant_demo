# 数据与文件重构迁移映射清单

> 状态：Draft for review
> 原则：本清单优先用于 review 与决策，不等于全部立即执行。

---

## 1. 迁移策略说明

本清单将当前文件分为 5 类动作：

- **保留**：当前路径继续保留，不迁移
- **归位**：建议迁到更明确的目录
- **归档**：建议移入 `archive/`
- **规范新增**：历史文件可不动，但后续新增必须遵守新落点
- **仅标注**：通过 README / 文档说明其语义，暂不物理移动

风险等级：

- **低**：几乎不影响运行，主要是文档、日志、报表、临时文件
- **中**：可能影响人工使用习惯，但不应影响系统主运行
- **高**：可能影响脚本、API、缓存或主数据读取

---

## 2. 顶层目录级别建议

| 当前路径 | 类型 | 建议动作 | 目标位置 | 风险 | 说明 |
|---|---|---|---|---|---|
| `docs/` | 正式文档 | 保留 | 原位 | 低 | 作为正式治理文档主目录 |
| `data/` | 共享数据 | 保留 | 原位 | 高 | 已有多脚本依赖 |
| `scripts/` | 顶层脚本 | 保留 | 原位 | 中 | 结构已较清晰 |
| `strategy/` | 离线策略产物 | 仅标注 | 原位 + README | 低 | 名称易误导，但短期不改名 |
| `output/` | 运行输出 | 保留 | 原位 | 中 | 可继续作为通用输出目录 |
| `ref_books/` | 参考资料 | 保留 | 原位 | 低 | 与业务代码边界清晰 |
| `.cache/` | 顶层缓存 | 保留 | 原位 | 中 | 避免误动 |
| 新增 `reports/` | 报告/记录 | 新建 | 顶层 | 低 | 收纳阶段笔记、人工分析、交叉检查 |
| 新增 `archive/` | 归档 | 新建 | 顶层 | 低 | 收纳历史遗留文件 |
| 新增 `experiments/` | 跨项目实验 | 新建 | 顶层 | 低 | 仅用于后续新规范 |

---

## 3. 顶层零散文件建议

| 当前路径 | 当前判断 | 建议动作 | 目标位置 | 风险 | 备注 |
|---|---|---|---|---|---|
| `0523_log.md` | 阶段日志 | 归位 | `reports/notes/2026-05-23-log.md` | 低 | 过程记录，不属于正式文档 |
| `0524_gpt.md` | 阶段记录 | 归位 | `reports/notes/2026-05-24-gpt-notes.md` | 低 | 同上 |
| `0525_gpt.md` | 阶段记录 | 归位 | `reports/notes/2026-05-25-gpt-notes.md` | 低 | 同上 |
| `0526_todo.md` | 阶段 TODO | 归位 | `reports/notes/2026-05-26-todo.md` | 低 | 历史工作记录 |
| `data_crosscheck_report.md` | 检查报告 | 归位 | `reports/data/data_crosscheck_report.md` | 低 | 更符合报告语义 |
| `trade_problem.md` | 主题文档 | review 后决定 | `docs/` 或 `reports/research/` | 中 | 先判断其是否为正式知识文档 |
| `trade_data_use.md` | 主题文档 | review 后决定 | `docs/` 或 `reports/research/` | 中 | 同上 |
| `web_keys.md` | 技术说明 | review 后决定 | `docs/operations/` 候选 | 中 | 需先判断现用性 |
| `QuarkMac_*.dmg` | 非项目文件 | 归档或移出仓库工作区 | `archive/external/` 候选 | 低 | 不建议留在代码仓库根目录 |

---

## 4. `stock_trade_demo/` 根目录治理建议

### 4.1 保留原位（核心运行）

| 当前路径 | 类型 | 建议动作 | 风险 | 说明 |
|---|---|---|---|---|
| `stock_trade_demo/web_app.py` | Web 入口 | 保留 | 高 | 当前正式入口 |
| `stock_trade_demo/choose_stock.py` | CLI 入口 | 保留 | 高 | 当前正式入口 |
| `stock_trade_demo/compare_strategies.py` | CLI 入口 | 保留 | 高 | 当前正式入口 |
| `stock_trade_demo/backtest.py` | 核心引擎 | 保留 | 高 | 代码核心 |
| `stock_trade_demo/chan_factors.py` | 核心库 | 保留 | 高 | 代码核心 |
| `stock_trade_demo/index_data.py` | 数据逻辑 | 保留 | 高 | 多链路依赖 |
| `stock_trade_demo/stock_data.csv` | 主数据 | 保留 | 高 | 当前主数据路径 |
| `stock_trade_demo/stock_data.parquet` | 主数据缓存 | 保留 | 高 | Web 优先读取路径之一 |
| `stock_trade_demo/.cache/` | 缓存目录 | 保留 | 高 | 当前运行依赖 |

### 4.2 文档建议

| 当前路径 | 当前判断 | 建议动作 | 目标位置 | 风险 | 说明 |
|---|---|---|---|---|---|
| `stock_trade_demo/README.md` | 子项目主说明 | 保留 | 原位 | 低 | 对外入口文档 |
| `stock_trade_demo/ChangeLog.md` | 变更记录 | 可归位 | `stock_trade_demo/docs/ChangeLog.md` | 低 | 若无代码引用可迁 |
| `stock_trade_demo/huice.md` | 子项目文档 | 可归位 | `stock_trade_demo/docs/huice.md` | 低 | 提高目录清晰度 |
| `stock_trade_demo/probe_entry_report.md` | 分析报告 | 归位 | `stock_trade_demo/reports/probes/probe_entry_report.md` | 低 | 更符合报告语义 |

### 4.3 生成产物建议

| 当前路径 | 当前判断 | 建议动作 | 目标位置 | 风险 | 说明 |
|---|---|---|---|---|---|
| `stock_trade_demo/选股策略详情.csv` | 报表产物 | 归位 | `stock_trade_demo/reports/selection/` | 低 | 生成产物不应长期留根目录 |
| `stock_trade_demo/选股策略详情_原版策略.csv` | 报表产物 | 归位 | `stock_trade_demo/reports/selection/` | 低 | 同上 |
| `stock_trade_demo/选股策略详情_缠论增强.csv` | 报表产物 | 归位 | `stock_trade_demo/reports/selection/` | 低 | 同上 |
| `stock_trade_demo/选股策略详情_纯缠论.csv` | 报表产物 | 归位 | `stock_trade_demo/reports/selection/` | 低 | 同上 |
| `stock_trade_demo/选股策略详情_Method A.csv` | 报表产物 | 归位 | `stock_trade_demo/reports/selection/` | 低 | 同上 |
| `stock_trade_demo/策略对比图表.png` | 图表产物 | 归位 | `stock_trade_demo/reports/plots/` | 低 | 与代码解耦 |

### 4.4 实验脚本建议

| 当前路径 | 当前判断 | 建议动作 | 目标位置 | 风险 | 说明 |
|---|---|---|---|---|---|
| `stock_trade_demo/final_optimization.py` | 实验/历史脚本 | 规范新增或后续迁移 | `stock_trade_demo/experiments/` | 中 | 先不强搬，避免习惯性调用中断 |
| `stock_trade_demo/regime_analysis.py` | 实验/研究脚本 | 规范新增或后续迁移 | `stock_trade_demo/experiments/` | 中 | 同上 |
| `stock_trade_demo/unused_factors_explore.py` | 实验脚本 | 规范新增或后续迁移 | `stock_trade_demo/experiments/` | 中 | 同上 |
| `stock_trade_demo/position_sizing_test.py` | 实验/优化脚本 | 规范新增或后续迁移 | `stock_trade_demo/experiments/` | 中 | 同上 |
| `stock_trade_demo/sell_side_optimize.py` | 实验/优化脚本 | 规范新增或后续迁移 | `stock_trade_demo/experiments/` | 中 | 同上 |
| `stock_trade_demo/run_overheat_ab_test.py` | 实验脚本 | 规范新增或后续迁移 | `stock_trade_demo/experiments/` | 中 | 同上 |
| `stock_trade_demo/run_weekly_experiment.py` | 已证伪方向实验 | 倾向归档 | `stock_trade_demo/archive/experiments/` | 中 | 符合 CLAUDE.md 的策略搜索 guidance |
| `stock_trade_demo/compare_probe_entry_report.py` | 分析辅助脚本 | 后续迁移 | `stock_trade_demo/experiments/` 或 `scripts/` | 中 | 需根据是否长期使用再定 |

### 4.5 临时脚本建议

| 当前路径 | 当前判断 | 建议动作 | 目标位置 | 风险 | 说明 |
|---|---|---|---|---|---|
| `stock_trade_demo/tmp_scan_csi1000.py` | 临时脚本 | 归档 | `stock_trade_demo/archive/tmp_scripts/` | 低 | 不应长期放根目录 |
| `stock_trade_demo/tmp_verify_timing_changelog.py` | 临时脚本 | 归档 | `stock_trade_demo/archive/tmp_scripts/` | 低 | 同上 |

### 4.6 研究/参考数据建议

| 当前路径 | 当前判断 | 建议动作 | 目标位置 | 风险 | 说明 |
|---|---|---|---|---|---|
| `stock_trade_demo/xingbuxing_stock_data.csv` | 历史/研究数据 | 候选归档 | `stock_trade_demo/archive/reference_data/` | 中 | 先确认是否还有脚本依赖 |
| `stock_trade_demo/所有可选因子在本文档第一行.xlsx` | 参考材料 | 可归位 | `stock_trade_demo/docs/` 或 `archive/reference_data/` | 低 | 不属于运行资产 |

---

## 5. `strategy/` 目录建议

| 当前路径 | 当前判断 | 建议动作 | 风险 | 说明 |
|---|---|---|---|---|
| `strategy/best_profile_*` | 择时配置产物 | 保留 | 高 | 当前 Web/API 依赖 |
| `strategy/walk_forward_log_*` | 离线日志产物 | 保留 | 中 | 后续可分组，但本期不动 |
| `strategy/holdout_report_*` | 报告产物 | 保留 | 中 | 后续可细分到 reports，但现阶段避免误伤 |
| `strategy/factor_signals_*` | 择时输入产物 | 保留 | 高 | 当前依赖较强 |
| `strategy/backtest_*` | 离线回测产物 | 保留 | 中 | 先不动 |
| `strategy/risk_signals.json` | Web 风险面板输入 | 保留 | 高 | 当前运行依赖 |
| `strategy/archive/` | 历史产物 | 保留 | 低 | 可继续作为归档层 |
| `strategy/README.md` | 说明文档 | 新建 | 低 | 建议新增说明其语义为“产物目录” |

---

## 6. 新增文件落点规范（未来生效）

### 6.1 顶层

| 文件类型 | 建议位置 |
|---|---|
| 正式治理文档 | `docs/` |
| 人工分析报告 | `reports/` |
| 工作日志/阶段记录 | `reports/notes/` |
| 归档材料 | `archive/` |
| 跨项目实验 | `experiments/` |

### 6.2 `stock_trade_demo/`

| 文件类型 | 建议位置 |
|---|---|
| 子项目专属说明文档 | `stock_trade_demo/docs/` |
| 选股/回测导出表格 | `stock_trade_demo/reports/selection/` |
| 图表输出 | `stock_trade_demo/reports/plots/` |
| 分析/探针报告 | `stock_trade_demo/reports/probes/` |
| 实验脚本 | `stock_trade_demo/experiments/` |
| 临时脚本 | `stock_trade_demo/archive/tmp_scripts/` 或 `tmp/` |

---

## 7. 本期建议立即执行的低风险对象

优先考虑以下对象：

1. 顶层零散日志与交叉检查报告
2. `stock_trade_demo/` 下的 `tmp_*` 脚本
3. `stock_trade_demo/` 下的 `选股策略详情*.csv`
4. `stock_trade_demo/策略对比图表.png`
5. 新建说明性 README 与治理文档

---

## 8. 本期明确不执行的对象

1. 主数据迁移
2. `.cache/` 大规模重构
3. `strategy/` 改名
4. 修改现有 Web/API 核心读取路径
5. 修改受保护实盘数据路径
