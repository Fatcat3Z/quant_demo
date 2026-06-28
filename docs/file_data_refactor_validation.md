# 数据与文件重构 Phase A-F 质量验收报告

> 验收日期：2026-06-28
> 验收范围：Phase A-F 数据与文件治理变更
> 当前状态：Phase F 代码与文档改动已完成；CLI 运行验证与垃圾文件清理由于 Bash 权限分类器暂不可用，待恢复后执行。

---

## 1. Phase F 变更目标

Phase F 解决 Phase A-E 验收中遗留的“当前常用脚本仍会把输出写回 `stock_trade_demo/` 根目录”的问题。

目标：

1. 当前常用 CLI / 辅助脚本默认输出到 `stock_trade_demo/reports/` 对应子目录。
2. 文档和 generated artifact 口径同步到新目录。
3. 只清理明确可再生垃圾；不处理主数据、缓存、strategy 关键产物和实盘记录。

---

## 2. 已完成的脚本输出路径治理

| 脚本 / 函数 | 旧默认输出 | 新默认输出 |
|---|---|---|
| `stock_trade_demo/choose_stock.py` | `stock_trade_demo/选股策略详情.csv` | `stock_trade_demo/reports/selection/选股策略详情.csv` |
| `stock_trade_demo/compare_strategies.py` | `stock_trade_demo/选股策略详情_{name}.csv` | `stock_trade_demo/reports/selection/选股策略详情_{name}.csv` |
| `stock_trade_demo/visualization.py::plot_strategy_comparison()` | `stock_trade_demo/策略对比图表.png` | `stock_trade_demo/reports/plots/策略对比图表.png` |
| `stock_trade_demo/visualization.py::plot_raw_style()` | `stock_trade_demo/选股对比图_{name}.png` | `stock_trade_demo/reports/plots/选股对比图_{name}.png` |
| `stock_trade_demo/compare_probe_entry_report.py` | `stock_trade_demo/probe_entry_report.md` | `stock_trade_demo/reports/probes/probe_entry_report.md` |

兼容性说明：

- `visualization.py` 保留 `save_path` / `save_dir` 显式参数语义；调用方显式传入路径时仍优先使用调用方路径。
- `choose_stock.py` 和 `compare_strategies.py` 未修改主数据读取路径，仍使用 `load_data('stock_data.csv')`。
- `compare_probe_entry_report.py` 只改报告输出位置，计算逻辑未改。

---

## 3. 已完成的文档与 ignore 口径同步

已更新：

- `CLAUDE.md`
  - 将 generated artifact policy 扩展到 `stock_trade_demo/reports/selection/`、`reports/plots/`、`reports/probes/`。
  - 保留旧根目录产物作为 legacy regenerated copies，便于识别和清理。
- `stock_trade_demo/reports/README.md`
  - 增加当前脚本输出映射。
  - 明确 `selection/*.csv` 与 `plots/*.png` 默认仍是 generated artifacts。
  - 明确主数据、缓存、实盘记录、`strategy` 关键产物不得迁入 reports。
- `stock_trade_demo/.gitignore`
  - 补充注释，说明裸文件名忽略规则会同时覆盖 reports 下同名可再生产物，这是有意行为。
- `docs/file_data_refactor_journal.md`
  - 新增 Phase F 执行记录。

---

## 4. 关键保护路径

本轮设计上未触碰以下路径：

- `data/live_trades.csv`
- `stock_trade_demo/stock_data.csv`
- `stock_trade_demo/stock_data.parquet`
- `stock_trade_demo/.cache/`
- `strategy/best_profile_*_timing.json`
- `strategy/risk_signals.json`
- 其他 Web/API 读取的 `strategy/` 关键产物

待 Bash 恢复后需再次用 git diff 验证这些路径未进入变更。

---

## 5. 待执行验证

由于当前 Bash 工具返回：

```text
gpt-5.5 is temporarily unavailable, so auto mode cannot determine the safety of Bash right now.
```

以下验证尚未执行：

1. CLI 输出路径验证：
   - `/Users/fatcat/opt/anaconda3/bin/python choose_stock.py --plot compare`
   - `/Users/fatcat/opt/anaconda3/bin/python compare_strategies.py --plot both`
   - `/Users/fatcat/opt/anaconda3/bin/python compare_probe_entry_report.py`
2. 旧根目录产物检查：
   - 不应重新生成 `stock_trade_demo/选股策略详情*.csv`
   - 不应重新生成 `stock_trade_demo/策略对比图表.png`
   - 不应重新生成 `stock_trade_demo/probe_entry_report.md`
3. 关键路径 diff 检查。
4. 最小垃圾文件清理：
   - `__pycache__/`
   - `.pytest_cache/`
   - `.DS_Store`
   - `.idea/workspace.xml`

---

## 6. 后续确认项

以下仍不在 Phase F 自动处理范围内，需要用户单独确认：

- `output/` 是否可删除
- `stock_trade_demo/.cache/archive/` weekly 大缓存是否外移或删除
- `QuarkMac*.dmg` 是否归档/移出仓库
- `stock_trade_demo/xingbuxing_stock_data.csv` 是否仍需保留
- `stock_trade_demo/所有可选因子在本文档第一行.xlsx` 是否归档
- `scripts/` 下历史研究脚本继续向 `strategy/` 输出的问题
