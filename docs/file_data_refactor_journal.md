# 数据与文件重构执行记录

> 本文档记录数据与文件治理项目的实际执行过程、迁移决策与验收结果。

---

## 2026-06-28：Phase A — 建立治理目录与说明文件

### 执行动作

新增顶层治理目录：

- `reports/`
- `reports/notes/`
- `reports/data/`
- `archive/`

新增 `stock_trade_demo` 子项目治理目录：

- `stock_trade_demo/docs/`
- `stock_trade_demo/reports/`
- `stock_trade_demo/reports/selection/`
- `stock_trade_demo/reports/plots/`
- `stock_trade_demo/reports/probes/`
- `stock_trade_demo/archive/tmp_scripts/`
- `stock_trade_demo/experiments/`

新增说明文件：

- `reports/README.md`
- `strategy/README.md`
- `stock_trade_demo/docs/README.md`
- `stock_trade_demo/reports/README.md`
- `stock_trade_demo/experiments/README.md`
- `stock_trade_demo/archive/README.md`

### 风险控制

- 未迁移核心数据
- 未迁移 `.cache/`
- 未迁移 `strategy/` 关键产物
- 未触碰 `data/live_trades.csv`
- 未修改 Web/API 运行路径

### 验收结论

Phase A 仅新增目录与说明文件，风险低，已完成。

---

## 2026-06-28：Phase B — 迁移低风险文本与记录文件

### 迁移前检查

迁移前检查了候选文件在仓库内的文本引用，发现：

- `0526_todo.md` 被 `docs/cache_miss_regression_2026-05-27.md` 引用
- `data_crosscheck_report.md` 被 `todo_list.md` 引用
- `0523_log.md` 内部包含旧路径自引用
- 其他候选文件主要只出现在本轮治理文档的迁移清单中

### 实际迁移

| 原路径 | 新路径 |
|---|---|
| `0523_log.md` | `reports/notes/2026-05-23-log.md` |
| `0524_gpt.md` | `reports/notes/2026-05-24-gpt-notes.md` |
| `0525_gpt.md` | `reports/notes/2026-05-25-gpt-notes.md` |
| `0526_todo.md` | `reports/notes/2026-05-26-todo.md` |
| `data_crosscheck_report.md` | `reports/data/data_crosscheck_report.md` |

### 同步更新的引用

- `docs/cache_miss_regression_2026-05-27.md`
  - `0526_todo.md` → `reports/notes/2026-05-26-todo.md`
- `todo_list.md`
  - `data_crosscheck_report.md` → `reports/data/data_crosscheck_report.md`
- `reports/notes/2026-05-23-log.md`
  - 更新了内部旧路径自引用

### 风险控制

- 迁移对象均为阶段日志、人工记录或检查报告
- 未迁移运行输入、主数据、缓存或策略产物
- 旧根目录文件已不存在，新路径文件均存在

### 验收结论

Phase B 已完成。剩余旧文件名引用主要来自本轮治理文档中的迁移清单和低风险计划，用于说明迁移前后关系，属于预期保留。

---

## 2026-06-28：Phase C — 归档临时脚本

### 迁移前检查

迁移前检查了候选临时脚本在仓库内的文本引用，发现：

- `stock_trade_demo/tmp_scan_csi1000.py` 仅出现在本轮治理文档的迁移清单与低风险计划中
- `stock_trade_demo/tmp_verify_timing_changelog.py` 仅出现在本轮治理文档的迁移清单与低风险计划中

未发现其他脚本、文档或配置对这两个临时脚本的显式依赖。

### 实际迁移

| 原路径 | 新路径 |
|---|---|
| `stock_trade_demo/tmp_scan_csi1000.py` | `stock_trade_demo/archive/tmp_scripts/tmp_scan_csi1000.py` |
| `stock_trade_demo/tmp_verify_timing_changelog.py` | `stock_trade_demo/archive/tmp_scripts/tmp_verify_timing_changelog.py` |

### 风险控制

- 迁移对象均为 `tmp_*` 临时脚本
- 未迁移主入口脚本
- 未迁移核心源码目录
- 未触碰主数据、缓存、实盘文件或 `strategy/` 关键产物
- 迁移后旧路径已不存在，新归档路径文件均存在

### 验收结论

Phase C 已完成。临时脚本已从 `stock_trade_demo/` 根目录归档到 `stock_trade_demo/archive/tmp_scripts/`，根目录噪声进一步降低。

---

## 2026-06-28：Phase D — 迁移报表、图表与探针产物

### 迁移前检查

迁移前检查了候选报表产物在仓库内的文本引用，发现：

- `stock_trade_demo/选股策略详情.csv`
  - 仍由 `stock_trade_demo/choose_stock.py` 输出
  - 归档脚本 `stock_trade_demo/archive/choose_stock_raw.py` 也仍输出同名文件
- `stock_trade_demo/策略对比图表.png`
  - 仍由 `stock_trade_demo/visualization.py` 输出
  - 也出现在 `stock_trade_demo/.gitignore` 与 `CLAUDE.md` 的生成产物说明中
- `stock_trade_demo/probe_entry_report.md`
  - 仍由 `stock_trade_demo/compare_probe_entry_report.py` 输出
- 其他策略详情 CSV 主要只出现在本轮治理文档的迁移清单与低风险计划中

根据低风险执行计划，本轮只迁移历史产物，不同步修改脚本输出路径；脚本输出目录治理留作后续单独处理。

### 实际迁移

| 原路径 | 新路径 |
|---|---|
| `stock_trade_demo/选股策略详情.csv` | `stock_trade_demo/reports/selection/选股策略详情.csv` |
| `stock_trade_demo/选股策略详情_原版策略.csv` | `stock_trade_demo/reports/selection/选股策略详情_原版策略.csv` |
| `stock_trade_demo/选股策略详情_缠论增强.csv` | `stock_trade_demo/reports/selection/选股策略详情_缠论增强.csv` |
| `stock_trade_demo/选股策略详情_纯缠论.csv` | `stock_trade_demo/reports/selection/选股策略详情_纯缠论.csv` |
| `stock_trade_demo/选股策略详情_Method A.csv` | `stock_trade_demo/reports/selection/选股策略详情_Method A.csv` |
| `stock_trade_demo/策略对比图表.png` | `stock_trade_demo/reports/plots/策略对比图表.png` |
| `stock_trade_demo/probe_entry_report.md` | `stock_trade_demo/reports/probes/probe_entry_report.md` |

### 风险控制

- 迁移对象为历史报表、图表与分析产物
- 未迁移主数据、缓存、实盘文件或 `strategy/` 关键产物
- 未修改当前 CLI / Web 的核心运行入口
- 由于部分脚本仍输出旧路径，后续若运行相关脚本，可能在 `stock_trade_demo/` 根目录重新生成同名产物；这属于后续输出路径治理问题，不影响当前运行
- 迁移后旧路径已不存在，新路径文件均存在

### 验收结论

Phase D 已完成。历史报表、图表与探针报告已归位到 `stock_trade_demo/reports/` 下的对应子目录。后续建议单独执行“脚本输出路径治理”，将 `choose_stock.py`、`visualization.py`、`compare_probe_entry_report.py` 的默认输出改到新 reports 结构。

---

## 2026-06-28：Phase E — 建立实验脚本规范

### 执行动作

本阶段只建立规范与登记清单，不迁移历史实验脚本。

已盘点并登记以下历史实验 / 研究脚本：

- `final_optimization.py`
- `regime_analysis.py`
- `unused_factors_explore.py`
- `position_sizing_test.py`
- `sell_side_optimize.py`
- `run_overheat_ab_test.py`
- `run_weekly_experiment.py`
- `compare_probe_entry_report.py`

已更新：

- `stock_trade_demo/experiments/README.md`

### 分类决策

- 大多数历史实验脚本先标记为“候选迁入 `stock_trade_demo/experiments/`”
- `run_weekly_experiment.py` 因 weekly / true-weekly 路线已不应优先重试，标记为“倾向归档到 `archive/experiments/`”
- `compare_probe_entry_report.py` 仍会输出旧根路径报告，后续应纳入“脚本输出路径治理”

### 风险控制

- 本阶段未移动任何历史实验脚本
- 未修改脚本行为
- 未修改运行入口或数据路径
- 只增强目录规则与后续迁移前检查清单

### 验收结论

Phase E 已完成。实验目录已有明确职责说明、候选脚本登记、后续迁移建议和迁移前检查清单。

---

## 2026-06-28：Phase F — 常用脚本输出路径治理与最小清理

### 脚本输出路径治理

已将当前仍在使用的 CLI / 辅助脚本默认输出从 `stock_trade_demo/` 根目录切换到 `stock_trade_demo/reports/`：

| 脚本 / 函数 | 新默认输出 |
|---|---|
| `choose_stock.py` | `reports/selection/选股策略详情.csv` |
| `compare_strategies.py` | `reports/selection/选股策略详情_{name}.csv` |
| `visualization.py::plot_strategy_comparison()` | `reports/plots/策略对比图表.png` |
| `visualization.py::plot_raw_style()` | `reports/plots/选股对比图_{name}.png` |
| `compare_probe_entry_report.py` | `reports/probes/probe_entry_report.md` |

### 文档与忽略规则同步

已同步：

- `CLAUDE.md`：更新 generated artifact policy，加入 reports 新路径与旧根路径兼容说明
- `stock_trade_demo/reports/README.md`：补充脚本输出映射、generated artifact 口径和禁止迁入项
- `stock_trade_demo/.gitignore`：补充注释，说明裸文件名规则会继续忽略 reports 下的可再生产物

### 最小清理范围

本阶段只允许清理明确可再生垃圾：

- `__pycache__/`
- `.pytest_cache/`
- `.DS_Store`
- `.idea/workspace.xml`

以下仍只记录为后续确认项，不在本阶段自动处理：

- `output/`
- `stock_trade_demo/.cache/archive/`
- `QuarkMac*.dmg`
- `stock_trade_demo/xingbuxing_stock_data.csv`
- `stock_trade_demo/所有可选因子在本文档第一行.xlsx`
- historical `scripts/` research outputs under `strategy/`

### 风险控制

- 未迁移主数据
- 未触碰 `.cache/`
- 未触碰 `strategy/` 关键产物
- 未触碰 `data/live_trades.csv`
- 保留 `visualization.py` 的 `save_path` / `save_dir` 显式参数语义

### 验收要求

运行常用 CLI 后，输出应生成在 `stock_trade_demo/reports/` 对应目录，且不应在 `stock_trade_demo/` 根目录重新生成同名 CSV/PNG/MD。
