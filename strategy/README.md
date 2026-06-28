# Strategy Artifacts

本目录当前用于存放**择时相关离线产物**，不是策略源码目录。

## 当前内容类型

- `best_profile_*_timing.json`：walk-forward 选出的默认参数配置
- `walk_forward_log_*.csv`：walk-forward 调参与回溯日志
- `holdout_report_*`：holdout 评估报告（`md` / `json`）
- `factor_signals_*.csv`：择时信号序列离线产物
- `backtest_*.csv`：离线回测结果
- `risk_signals.json`：Web 风险面板读取的离线风险信号

## 管理原则

1. 本目录短期内保持原路径不变，避免误伤现有 Web/API/脚本依赖。
2. 如需调整结构，应优先在文档层澄清语义，再做小步迁移。
3. 不要把新的源码文件放到这里；源码应继续进入 `stock_trade_demo/strategies/` 或相关代码目录。
