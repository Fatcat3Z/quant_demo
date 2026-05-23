#!/usr/bin/env python
"""离线递进微调 pipeline (Phase 2)

为 5 个 timing 策略（csi1000/star50/chinext/nasdaq/sp500）做参数网格搜索：

1. 训练 cutoff = 2025-11-30；所有 fit / score 都只用 cutoff 之前的数据。
2. 对每个参数组合：在 cutoff 之前的 panel 上跑一次 run_timing_backtest，
   再用 filter_timing_result(start, end=cutoff) 触发 cold-start 重算，分别
   在 6m (2025-06-01→cutoff) 和 1y (2024-12-01→cutoff) 两个窗口上计算 Calmar。
3. 评分: score = 0.6 * Calmar(6m) + 0.4 * Calmar(1y)
4. 风险约束: 任一窗口 |maxDD| > 0.20 ⇒ score = -inf
5. 最优组合写入 strategy/best_profile_{name}.json；全网格审计日志写入
   strategy/walk_forward_log_{name}.csv

CLAUDE.md Rule 12: 离线脚本一次性算完，web 层只读 best_profile_*.json。
CLAUDE.md Rule 13: cold-start 重算确保窗口内资金从 initial_capital 重置。

运行方式:
    /Users/fatcat/opt/anaconda3/bin/python scripts/walk_forward_train.py
    /Users/fatcat/opt/anaconda3/bin/python scripts/walk_forward_train.py --only csi1000_timing
    /Users/fatcat/opt/anaconda3/bin/python scripts/walk_forward_train.py --dry-run
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
_DEMO_ROOT = os.path.join(_REPO_ROOT, 'stock_trade_demo')
sys.path.insert(0, _DEMO_ROOT)

from index_data import build_index_panel, build_us_index_panel  # noqa: E402
from timing.backtest import (  # noqa: E402
    evaluate_timing_result,
    filter_timing_result,
    run_timing_backtest,
)
from timing.strategies import (  # noqa: E402
    ChiNextTimingStrategy,
    CSI1000TimingStrategy,
    NasdaqTimingStrategy,
    SP500TimingStrategy,
    Star50TimingStrategy,
)


TRAINING_CUTOFF = pd.Timestamp('2025-11-30')
WINDOW_6M_START = pd.Timestamp('2025-06-01')
WINDOW_1Y_START = pd.Timestamp('2024-12-01')

# v2 评分公式（修正后记 2026-05-23）：把 cutoff 之前的"全历史"Calmar 也纳入加权，
# 避免上一版只看近端 6m/1y Calmar 导致 csi1000 全历史年化从 4.57% 跌到 0.98%。
# score = 0.4 * Calmar(recent_6m) + 0.3 * Calmar(recent_1y) + 0.3 * Calmar(full_pre_cutoff)
SCORE_WEIGHTS = {'recent_6m': 0.4, 'recent_1y': 0.3, 'full_pre_cutoff': 0.3}
# 任一窗口 |maxDD| > MAX_DD_THRESHOLD ⇒ 该参数组合被丢弃
MAX_DD_THRESHOLD = 0.20
# 全历史不退步硬约束：候选必须满足 full_final_nav >= FULL_NAV_FLOOR_RATIO * default_full_nav
# 其中 default 取 STRATEGY_SPECS 里的"出厂 tuned"（即 timing/strategies.py:__init__ 默认值）。
# 全部数据仍只用 cutoff 之前的 panel，无 look-ahead。
# 2026-05-23 收紧到 1.00（用户要求"收益不能下降"）。任何 candidate 必须 full_nav >= default 才能入选；
# 否则一律 fallback_to_default。
FULL_NAV_FLOOR_RATIO = 1.00
# 出厂 tuned（必须与 timing/strategies.py 各策略类 __init__ 默认值保持一致）。
# 用于 FULL_NAV_FLOOR_RATIO 约束的基准点。
DEFAULT_TUNED = {
    'csi1000_timing': {'breakout_window': 15, 'exit_window': 7, 'trend_window': 50},
    'star50_timing':  {'breakout_window': 10, 'exit_window': 5, 'trend_window': 40},
    'chinext_timing': {'momentum_short_window': 15, 'momentum_long_window': 40,
                       'trend_window': 40, 'momentum_threshold': 0.02},
    'nasdaq_timing':  {'fast_window': 20, 'slow_window': 120, 'momentum_window': 120},
    'sp500_timing':   {'fast_window': 20, 'slow_window': 125, 'momentum_window': 100},
}

OUTPUT_DIR = os.path.join(_REPO_ROOT, 'strategy')


SHARED_REALISM = {
    'profit_lock_enabled': False,
    'profit_lock_drawdown': 0.04,
    'profit_lock_level_1': 0.10,
    'profit_lock_level_2': 0.18,
    'profit_lock_level_3': 0.28,
    'slippage_bps': 5.0,
    'cash_interest_rate': 0.015,
    'commission_rate': 0.0001,
    'commission_min': 5.0,
    'stamp_tax_rate': 0.0,
    'transfer_fee_rate': 0.00001,
    'limit_max_delay_days': 5,
}


# 每个策略包含: cls, panel_kind ('cn'/'us'), base_defaults, grid, tunable_keys
STRATEGY_SPECS = {
    'csi1000_timing': {
        'cls': CSI1000TimingStrategy,
        'panel': 'cn',
        'base': {
            'exposure_mode': 'staged', 'enter_threshold': 0.55, 'add_threshold': 0.75,
            'trim_threshold': 0.38, 'exit_threshold': 0.18, 'confirm_days': 1,
            'max_entry_exposure': 0.5, 'probe_entry_exposure': 0.25, 'probe_confirm_days': 1,
        },
        'grid': {
            'breakout_window': [10, 15, 20, 25],
            'exit_window': [5, 7, 10],
            'trend_window': [30, 50, 80],
        },
    },
    'star50_timing': {
        'cls': Star50TimingStrategy,
        'panel': 'cn',
        'base': {
            'exposure_mode': 'staged', 'enter_threshold': 0.55, 'add_threshold': 0.75,
            'trim_threshold': 0.35, 'exit_threshold': 0.15, 'confirm_days': 1,
            'max_entry_exposure': 0.5, 'probe_entry_exposure': 0.25, 'probe_confirm_days': 1,
        },
        'grid': {
            'breakout_window': [8, 10, 15, 20],
            'exit_window': [3, 5, 8],
            'trend_window': [30, 40, 60],
        },
    },
    'chinext_timing': {
        'cls': ChiNextTimingStrategy,
        'panel': 'cn',
        'base': {
            'exposure_mode': 'staged', 'enter_threshold': 0.6, 'add_threshold': 0.8,
            'trim_threshold': 0.35, 'exit_threshold': 0.15, 'confirm_days': 2,
            'max_entry_exposure': 0.5, 'probe_entry_exposure': 0.25, 'probe_confirm_days': 1,
        },
        'grid': {
            'momentum_short_window': [10, 15, 20],
            'momentum_long_window': [30, 40, 60],
            'trend_window': [30, 40, 60],
            'momentum_threshold': [0.0, 0.01, 0.02],
        },
    },
    'nasdaq_timing': {
        'cls': NasdaqTimingStrategy,
        'panel': 'us',
        'base': {
            'exposure_mode': 'staged', 'enter_threshold': 0.55, 'add_threshold': 0.75,
            'trim_threshold': 0.35, 'exit_threshold': 0.15, 'confirm_days': 2,
            'max_entry_exposure': 0.5,
        },
        'grid': {
            'fast_window': [15, 20, 25],
            'slow_window': [100, 120, 150],
            'momentum_window': [100, 120, 150],
        },
    },
    'sp500_timing': {
        'cls': SP500TimingStrategy,
        'panel': 'us',
        'base': {
            'exposure_mode': 'staged', 'enter_threshold': 0.5, 'add_threshold': 0.72,
            'trim_threshold': 0.32, 'exit_threshold': 0.14, 'confirm_days': 2,
            'max_entry_exposure': 0.5,
        },
        'grid': {
            'fast_window': [15, 20, 30],
            'slow_window': [100, 125, 150],
            'momentum_window': [80, 100, 125],
        },
    },
}


def _build_strategy(spec, grid_point):
    """构造策略实例：base 默认 + grid_point 覆盖；realism 通过 setattr 注入。"""
    init_params = dict(spec['base'])
    init_params.update(grid_point)
    instance = spec['cls'](**init_params)
    # 把 realism 参数 setattr 到实例上 (与 web_app.build_timing_strategy 行为一致)
    for k, v in SHARED_REALISM.items():
        setattr(instance, k, v)
    return instance


def _extract_metric_floats(metrics: dict) -> dict:
    """把 evaluate_timing_result 返回的 % 字符串转成原始 float。"""
    out = {}
    cum = metrics.get('累积净值')
    out['final_nav'] = float(cum) if cum is not None else float('nan')

    ann = metrics.get('年化收益', '')
    if isinstance(ann, str) and ann.endswith('%'):
        try:
            out['annual_return'] = float(ann.rstrip('%')) / 100.0
        except ValueError:
            out['annual_return'] = float('nan')
    else:
        out['annual_return'] = float('nan')

    mdd = metrics.get('最大回撤', '')
    if isinstance(mdd, str) and mdd.endswith('%'):
        try:
            out['max_drawdown'] = float(mdd.rstrip('%')) / 100.0  # 负数
        except ValueError:
            out['max_drawdown'] = float('nan')
    else:
        out['max_drawdown'] = float('nan')

    calmar = metrics.get('年化收益/回撤比')
    out['calmar'] = float(calmar) if calmar is not None else float('nan')

    out['rebalance_count'] = int(metrics.get('调仓次数', 0))
    out['avg_exposure'] = float(metrics.get('平均仓位', 0.0))
    return out


def _evaluate_one(spec, grid_point, panel_pre_cutoff, default_full_nav=None):
    """在 cutoff 之前的 panel 上跑回测，并在 6m/1y/full_pre_cutoff 三窗口上做 cold-start 评分。

    v2 评分（修正后记 2026-05-23）：
      - score = 0.4*Calmar(6m) + 0.3*Calmar(1y) + 0.3*Calmar(full_pre_cutoff)
      - 任一窗口 |maxDD| > MAX_DD_THRESHOLD ⇒ 丢弃
      - 若提供 default_full_nav，则要求 full_pre_cutoff 的 final_nav ≥ FULL_NAV_FLOOR_RATIO*default_full_nav，
        否则丢弃。该约束保证 best 不会以"换全历史收益"换近端 Calmar。
    """
    strategy = _build_strategy(spec, grid_point)
    signal_df = strategy.run(panel_pre_cutoff.copy())
    full_result = run_timing_backtest(signal_df, strategy, benchmark_returns=None)

    panel_end = pd.to_datetime(panel_pre_cutoff['交易日期'].max())
    windows = {
        'recent_6m': (WINDOW_6M_START, TRAINING_CUTOFF),
        'recent_1y': (WINDOW_1Y_START, TRAINING_CUTOFF),
        'full_pre_cutoff': (pd.to_datetime(panel_pre_cutoff['交易日期'].min()), panel_end),
    }
    window_metrics = {}
    for name, (start, end) in windows.items():
        sliced = filter_timing_result(full_result, start_date=start, end_date=end)
        if len(sliced) == 0:
            window_metrics[name] = None
            continue
        m = evaluate_timing_result(sliced, benchmark_returns=None, reset_capital=True)
        window_metrics[name] = _extract_metric_floats(m)

    # 评分
    score = 0.0
    discard_reason = None
    for name, weight in SCORE_WEIGHTS.items():
        wm = window_metrics.get(name)
        if wm is None or np.isnan(wm['calmar']):
            score = float('-inf')
            discard_reason = f'{name} 无法计算 Calmar'
            break
        if abs(wm['max_drawdown']) > MAX_DD_THRESHOLD:
            score = float('-inf')
            discard_reason = f'{name} maxDD={wm["max_drawdown"]:.4f} 超过阈值 {MAX_DD_THRESHOLD}'
            break
        score += weight * wm['calmar']

    # 全历史不退步硬约束（仅当传入了 default_full_nav 才生效）
    if discard_reason is None and default_full_nav is not None:
        full_wm = window_metrics.get('full_pre_cutoff') or {}
        full_nav = full_wm.get('final_nav')
        if full_nav is None or np.isnan(full_nav):
            discard_reason = 'full_pre_cutoff final_nav 无法计算'
            score = float('-inf')
        else:
            floor = FULL_NAV_FLOOR_RATIO * default_full_nav
            if full_nav < floor:
                discard_reason = (f'full_pre_cutoff final_nav={full_nav:.4f} < floor={floor:.4f} '
                                  f'(={FULL_NAV_FLOOR_RATIO:.2f}*default {default_full_nav:.4f})')
                score = float('-inf')

    return {
        'grid_point': grid_point,
        'windows': window_metrics,
        'score': score,
        'discarded': discard_reason,
    }


def _grid_iter(grid: dict):
    keys = list(grid.keys())
    for values in itertools.product(*(grid[k] for k in keys)):
        yield dict(zip(keys, values))


def _slice_panel_pre_cutoff(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy()
    df['交易日期'] = pd.to_datetime(df['交易日期'])
    return df[df['交易日期'] <= TRAINING_CUTOFF].reset_index(drop=True)


def _run_for_strategy(strategy_id: str, panel_pre_cutoff: pd.DataFrame,
                      dry_run: bool = False) -> dict:
    spec = STRATEGY_SPECS[strategy_id]
    grid_points = list(_grid_iter(spec['grid']))
    print(f"\n=== {strategy_id}: {len(grid_points)} grid points ===", flush=True)
    if dry_run:
        for gp in grid_points[:5]:
            print('  sample:', gp)
        print(f'  ... ({len(grid_points)} total, --dry-run 不执行回测)')
        return {'strategy': strategy_id, 'grid_size': len(grid_points), 'dry_run': True}

    # 先跑一次"出厂 tuned"作为全历史 final_nav 基准点。
    default_tuned = DEFAULT_TUNED.get(strategy_id)
    default_full_nav = None
    default_metrics = None
    if default_tuned is not None:
        print(f"  [default-floor] 跑出厂 tuned 作为 full_pre_cutoff 基准: {default_tuned}", flush=True)
        try:
            default_res = _evaluate_one(spec, default_tuned, panel_pre_cutoff, default_full_nav=None)
            default_metrics = default_res['windows']
            full_wm = (default_metrics.get('full_pre_cutoff') or {}) if default_metrics else {}
            default_full_nav = full_wm.get('final_nav')
            if default_full_nav and not np.isnan(default_full_nav):
                print(f"    default full_pre_cutoff final_nav = {default_full_nav:.4f}; "
                      f"floor = {FULL_NAV_FLOOR_RATIO:.2f}x = {FULL_NAV_FLOOR_RATIO*default_full_nav:.4f}",
                      flush=True)
            else:
                print(f"    [WARN] default full_pre_cutoff final_nav 无法计算，floor 约束将被关闭")
                default_full_nav = None
        except Exception as e:
            print(f"    [WARN] default-floor 计算异常: {e!r}; floor 约束将被关闭")
            default_full_nav = None

    log_rows = []
    best = None
    t0 = time.time()
    for i, gp in enumerate(grid_points, 1):
        try:
            res = _evaluate_one(spec, gp, panel_pre_cutoff, default_full_nav=default_full_nav)
        except Exception as e:
            print(f"  [{i:>3}/{len(grid_points)}] {gp} -> EXCEPTION {e!r}")
            log_rows.append({**gp, 'score': float('-inf'), 'discarded': f'exception: {e!r}'})
            continue

        row = dict(gp)
        row['score'] = res['score']
        row['discarded'] = res['discarded'] or ''
        for win_name, win_metrics in res['windows'].items():
            if win_metrics is None:
                row[f'{win_name}_calmar'] = float('nan')
                row[f'{win_name}_maxdd'] = float('nan')
                row[f'{win_name}_annret'] = float('nan')
                continue
            row[f'{win_name}_calmar'] = win_metrics['calmar']
            row[f'{win_name}_maxdd'] = win_metrics['max_drawdown']
            row[f'{win_name}_annret'] = win_metrics['annual_return']
        log_rows.append(row)

        if (i % 10 == 0) or i == len(grid_points):
            elapsed = time.time() - t0
            rate = i / max(elapsed, 1e-6)
            eta = (len(grid_points) - i) / max(rate, 1e-6)
            print(f"  [{i:>3}/{len(grid_points)}] elapsed={elapsed:.1f}s rate={rate:.2f}/s eta={eta:.1f}s "
                  f"best_so_far={(best or {}).get('score', float('-inf')):.4f}", flush=True)

        if res['discarded']:
            continue
        if best is None or res['score'] > best['score']:
            best = res

    elapsed_total = time.time() - t0
    print(f"  完成 {len(grid_points)} 组合, 总耗时 {elapsed_total:.1f}s", flush=True)

    # 全量日志写盘
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_df = pd.DataFrame(log_rows)
    log_path = os.path.join(OUTPUT_DIR, f'walk_forward_log_{strategy_id}.csv')
    log_df.sort_values('score', ascending=False).to_csv(log_path, index=False)
    print(f"  全网格日志 -> {log_path}", flush=True)

    fallback_used = False
    if best is None:
        if default_tuned is not None and default_metrics is not None:
            print(f"  [WARN] {strategy_id}: 无组合通过 maxDD<{MAX_DD_THRESHOLD} + full-nav-floor 约束；"
                  f"回退到出厂 tuned {default_tuned}")
            best = {
                'grid_point': dict(default_tuned),
                'windows': default_metrics,
                'score': float('nan'),  # fallback 不参与排序
                'discarded': 'fallback_to_default',
            }
            fallback_used = True
        else:
            print(f"  [WARN] {strategy_id}: 无任何组合通过约束，且无出厂 tuned 可回退，未写 best_profile")
            return {'strategy': strategy_id, 'best': None, 'grid_size': len(grid_points)}

    # best profile：base 默认 + grid_point 覆盖（保留 staged/threshold 等基线参数）
    best_params = dict(spec['base'])
    best_params.update(best['grid_point'])
    profile = {
        'strategy_id': strategy_id,
        'training_cutoff': TRAINING_CUTOFF.strftime('%Y-%m-%d'),
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'score_formula': (f"{SCORE_WEIGHTS['recent_6m']}*Calmar(6m) + "
                          f"{SCORE_WEIGHTS['recent_1y']}*Calmar(1y) + "
                          f"{SCORE_WEIGHTS['full_pre_cutoff']}*Calmar(full_pre_cutoff)  "
                          f"[floor: full_nav >= {FULL_NAV_FLOOR_RATIO:.2f}*default]"),
        'maxdd_threshold': MAX_DD_THRESHOLD,
        'full_nav_floor_ratio': FULL_NAV_FLOOR_RATIO,
        'default_full_nav': default_full_nav,
        'fallback_to_default': fallback_used,
        'score': best['score'],
        'tuned_params': best['grid_point'],
        'all_params': best_params,
        'window_metrics': best['windows'],
        'grid_size': len(grid_points),
    }
    out_path = os.path.join(OUTPUT_DIR, f'best_profile_{strategy_id}.json')
    with open(out_path, 'w') as f:
        json.dump(profile, f, ensure_ascii=False, indent=2, default=float)
    print(f"  best profile -> {out_path}")
    print(f"    score={best['score']:.4f}  params={best['grid_point']}")
    for wname, wm in best['windows'].items():
        if wm is None:
            continue
        print(f"    {wname}: calmar={wm['calmar']:.3f}  maxDD={wm['max_drawdown']:.3%}  annRet={wm['annual_return']:.3%}")
    return {'strategy': strategy_id, 'best': best, 'grid_size': len(grid_points)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', action='append', default=None,
                        help='只跑指定 strategy_id，可重复传')
    parser.add_argument('--dry-run', action='store_true',
                        help='只打印 grid 大小，不实际跑回测')
    args = parser.parse_args()

    target_ids = args.only or list(STRATEGY_SPECS.keys())
    cn_ids = [sid for sid in target_ids if STRATEGY_SPECS[sid]['panel'] == 'cn']
    us_ids = [sid for sid in target_ids if STRATEGY_SPECS[sid]['panel'] == 'us']

    cn_panel = us_panel = None
    if cn_ids and not args.dry_run:
        print('[load] build_index_panel() ...', flush=True)
        t0 = time.time()
        cn_panel = _slice_panel_pre_cutoff(build_index_panel())
        print(f'[load] CN panel rows={len(cn_panel)}  date_range=[{cn_panel["交易日期"].min()} .. {cn_panel["交易日期"].max()}]  ({time.time()-t0:.1f}s)')
    if us_ids and not args.dry_run:
        print('[load] build_us_index_panel() ...', flush=True)
        t0 = time.time()
        us_panel = _slice_panel_pre_cutoff(build_us_index_panel())
        print(f'[load] US panel rows={len(us_panel)}  date_range=[{us_panel["交易日期"].min()} .. {us_panel["交易日期"].max()}]  ({time.time()-t0:.1f}s)')

    summary = []
    for sid in target_ids:
        spec = STRATEGY_SPECS[sid]
        panel = cn_panel if spec['panel'] == 'cn' else us_panel
        summary.append(_run_for_strategy(sid, panel, dry_run=args.dry_run))

    print('\n=== Walk-forward training summary ===')
    for s in summary:
        if s.get('dry_run'):
            print(f"  {s['strategy']:>18}  grid_size={s['grid_size']}  [dry-run]")
            continue
        best = s.get('best')
        if best is None:
            print(f"  {s['strategy']:>18}  grid_size={s['grid_size']}  best=NONE (全部被 maxDD 约束丢弃)")
            continue
        print(f"  {s['strategy']:>18}  grid_size={s['grid_size']}  score={best['score']:.4f}  params={best['grid_point']}")


if __name__ == '__main__':
    main()
