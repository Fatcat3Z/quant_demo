# Holdout 报告 — sp500_timing

- 生成时间: 2026-05-23T18:59:52
- 训练 cutoff: 2025-11-30
- Holdout 区间: **2025-12-01 ~ 2026-05-21**  (112 bars)
- Profile 来源: strategy/best_profile_sp500_timing.json

## 调参网格选出的最优参数
| 参数 | 取值 |
|------|------|
| `fast_window` | `30` |
| `slow_window` | `100` |
| `momentum_window` | `80` |

## 训练区评分（来自 walk-forward 选优阶段）
- 评分公式: `0.6*Calmar(6m) + 0.4*Calmar(1y)`
- 综合分: **3.6200**  (maxDD 阈值 0.2)

| 窗口 | Calmar | 年化收益 | 最大回撤 | 平均仓位 | 调仓次数 |
|------|--------|----------|----------|----------|----------|
| recent_6m | 5.620 | 29.06% | -5.17% | 72.76% | 16 |
| recent_1y | 0.620 | 5.89% | -9.53% | 47.52% | 32 |

## Holdout 区间表现（**只读，未参与选优**）
| 指标 | 取值 |
|------|------|
| 累积净值 | 0.9574 |
| 年化收益 | -8.87% |
| 最大回撤 | -5.18% |
| Calmar | -1.710 |
| 平均仓位 | 20.09% |
| 调仓次数 | 24 |

### 训练区 vs Holdout Calmar 对比
| 窗口 | Calmar |
|------|--------|
| 训练区 recent_6m | 5.620 |
| 训练区 recent_1y | 0.620 |
| **Holdout** | **-1.710** |

> 如果 holdout Calmar 显著低于训练区，说明该参数对训练区过拟合；
> 如果接近或更高，说明 walk-forward 选出的参数在 OOS 上稳定。

---

*由 `scripts/build_holdout_reports.py` 自动生成。Holdout 报告只读不参与选优；
如需调整 holdout 起点，请同步修改 `web_app.py` 的 `HOLDOUT_START`。*
