# stock_trade_demo Reports

本目录用于存放 `stock_trade_demo` 子项目的**报表、图表与分析输出**，避免这些生成产物长期混放在项目根目录。

## 目录约定

- `selection/`：选股明细、导出表格、策略详情 CSV
- `plots/`：对比图、可视化输出 PNG 等
- `probes/`：探针报告、分析报告、诊断说明

## 当前脚本输出映射

- `choose_stock.py` → `reports/selection/选股策略详情.csv`
- `compare_strategies.py` → `reports/selection/选股策略详情_{name}.csv`
- `visualization.py::plot_strategy_comparison()` → `reports/plots/策略对比图表.png`
- `visualization.py::plot_raw_style()` → `reports/plots/选股对比图_{name}.png`
- `compare_probe_entry_report.py` → `reports/probes/probe_entry_report.md`

## 使用原则

1. 这里应主要存放**可再生成的输出文件**，而不是运行所需输入。
2. 新增报表类输出时，优先落到本目录的对应子目录中。
3. 主数据、缓存、核心入口不要迁到本目录。
4. `selection/*.csv` 与 `plots/*.png` 默认仍是 generated artifacts，通常不提交到 git。
5. `probes/*.md` 是否保留，取决于报告本身是否有长期追溯价值。

## 禁止迁入

以下文件/目录不得为了“目录整齐”迁入 reports：

- `stock_data.csv` / `stock_data.parquet`
- `.cache/`
- `data/live_trades.csv`
- `strategy/best_profile_*`、`strategy/risk_signals.json` 等 Web/API 读取的离线产物
