# Holdout 报告 — star50_timing

- 生成时间: 2026-05-23T18:59:51
- 训练 cutoff: 2025-11-30
- Holdout 区间: **2025-12-01 ~ 2026-05-21**  (112 bars)
- Profile 来源: strategy/best_profile_star50_timing.json

## 调参网格选出的最优参数
| 参数 | 取值 |
|------|------|
| `breakout_window` | `8` |
| `exit_window` | `3` |
| `trend_window` | `60` |

## 训练区评分（来自 walk-forward 选优阶段）
- 评分公式: `0.6*Calmar(6m) + 0.4*Calmar(1y)`
- 综合分: **10.6700**  (maxDD 阈值 0.2)

| 窗口 | Calmar | 年化收益 | 最大回撤 | 平均仓位 | 调仓次数 |
|------|--------|----------|----------|----------|----------|
| recent_6m | 10.670 | 89.71% | -8.40% | 35.14% | 10 |
| recent_1y | 10.670 | 89.71% | -8.40% | 35.14% | 10 |

## Holdout 区间表现（**只读，未参与选优**）
| 指标 | 取值 |
|------|------|
| 累积净值 | 1.3085 |
| 年化收益 | 77.53% |
| 最大回撤 | -4.06% |
| Calmar | 19.110 |
| 平均仓位 | 32.81% |
| 调仓次数 | 10 |

### 训练区 vs Holdout Calmar 对比
| 窗口 | Calmar |
|------|--------|
| 训练区 recent_6m | 10.670 |
| 训练区 recent_1y | 10.670 |
| **Holdout** | **19.110** |

> 如果 holdout Calmar 显著低于训练区，说明该参数对训练区过拟合；
> 如果接近或更高，说明 walk-forward 选出的参数在 OOS 上稳定。

---

*由 `scripts/build_holdout_reports.py` 自动生成。Holdout 报告只读不参与选优；
如需调整 holdout 起点，请同步修改 `web_app.py` 的 `HOLDOUT_START`。*
