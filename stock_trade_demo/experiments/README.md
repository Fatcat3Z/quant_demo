# stock_trade_demo Experiments

本目录用于收纳 `stock_trade_demo` 的**实验脚本、研究性尝试与非生产默认流程**。

## 适合放入本目录的内容

- 一次性实验脚本
- 已被验证但暂不进入默认生产路径的研究脚本
- 参数敏感性 / 风格切换 / 对比实验相关脚本
- 不应作为 Web/API 或常规 CLI 默认入口的研究代码

## 暂行规则

1. 本轮重构先建立目录与规则，不立即强制迁移所有历史实验脚本。
2. 后续新增实验脚本应优先放到这里，而不是继续堆在 `stock_trade_demo/` 根目录。
3. 已证伪或长期不再使用的实验，可进一步移入 `stock_trade_demo/archive/`。
4. 如果某个实验脚本被文档、人工流程或外部命令频繁调用，迁移前应先建立 wrapper 或更新调用说明。

---

## 当前历史实验脚本盘点（2026-06-28）

以下文件当前仍保留在 `stock_trade_demo/` 根目录，本轮只登记，不迁移。

| 文件 | 当前判断 | 后续建议 | 备注 |
|---|---|---|---|
| `final_optimization.py` | 历史优化 / 实验脚本 | 候选迁入 `experiments/` | CLAUDE.md 已标记为 legacy / experimental |
| `regime_analysis.py` | regime 分析脚本 | 候选迁入 `experiments/` | CLAUDE.md 已标记为 legacy / experimental |
| `unused_factors_explore.py` | 因子探索脚本 | 候选迁入 `experiments/` | CLAUDE.md 已标记为 legacy / experimental |
| `position_sizing_test.py` | 仓位 sizing 实验 | 候选迁入 `experiments/` | 生成产物已在 .gitignore 中有规则 |
| `sell_side_optimize.py` | 卖出侧优化实验 | 候选迁入 `experiments/` | 生成产物已在 .gitignore 中有规则 |
| `run_overheat_ab_test.py` | 过热 AB 实验 | 候选迁入 `experiments/` | 与策略研究相关，暂不作为默认路径 |
| `run_weekly_experiment.py` | weekly / true-weekly 实验 | 倾向归档到 `archive/experiments/` | CLAUDE.md 提示 weekly 方向已不应优先重试 |
| `compare_probe_entry_report.py` | probe 报告生成辅助脚本 | 候选迁入 `experiments/` 或 `scripts/` | 当前仍会输出 `probe_entry_report.md` 到旧根路径，后续应治理输出目录 |

---

## 新增实验脚本命名建议

建议后续新增实验脚本使用以下命名：

- `experiment_<topic>.py`
- `probe_<topic>.py`
- `audit_<topic>.py`
- `compare_<topic>.py`

如果脚本会生成文件，应显式写入：

- `stock_trade_demo/reports/`：报表、图表、分析输出
- `stock_trade_demo/archive/`：归档材料
- `stock_trade_demo/.cache/`：可重建缓存

不要默认输出到 `stock_trade_demo/` 根目录。

---

## 后续迁移前检查清单

迁移历史实验脚本前，应先确认：

1. 是否被 README、CLAUDE.md、脚本或外部流程显式引用
2. 是否依赖当前工作目录为 `stock_trade_demo/`
3. 是否用相对路径读取主数据或缓存
4. 是否会输出报表到根目录
5. 是否需要保留原路径 wrapper
6. 是否应该迁入 `experiments/`，还是直接进入 `archive/`
