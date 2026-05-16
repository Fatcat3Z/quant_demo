"""
邢不行-股票量化入门训练营 + 缠论因子增强版
Day3：选股策略示例

Chan Theory因素集成 (Task 1.1 + Method A):
  对应 quant_factor.md Sections 10-14，从 stock_data.csv 的 OHLC + MACD 列
  计算缠论分型、背驰、中枢位置、笔强度、买卖点信号等可复用因子。

Method A (v2.0): 使用 chan_monthly_factor_builder.py 的日线缠论流水线 →
月度聚合因子，替换原有的月度代理近似计算。

策略对比：
  python3 choose_stock.py --mode compare      # 原版 vs 缠论增强 vs Method A (默认)
  python3 choose_stock.py --mode original     # 仅原版
  python3 choose_stock.py --mode chan         # 仅缠论增强
  python3 choose_stock.py --mode method_a     # Method A 日线流水线因子
"""
import ast
import sys
import os
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

warnings.filterwarnings('ignore')

# 中文字体配置
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'STHeiti', 'Arial Unicode MS', 'SimHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

pd.set_option('expand_frame_repr', False)

# === 选股参数
select_stock_num = 6
c_rate = 1.2 / 10000
t_rate = 1 / 1000
sell_cost = c_rate + t_rate

BULL_TP = 0.30
BEAR_TP = 0.22
BULL_N = 6
BEAR_N = 4


def safe_float(series, default=0.0):
    return pd.to_numeric(series, errors='coerce').fillna(default)


def load_data():
    df = pd.read_csv('stock_data.csv', encoding='gbk',
                     parse_dates=['交易日期'], low_memory=False)
    mkt_ret = df.groupby('交易日期')['涨跌幅'].mean()
    mkt_cum = (1 + mkt_ret).cumprod()
    mkt_ma12 = mkt_cum.rolling(12).mean()
    df['市场状态'] = df['交易日期'].map(
        (mkt_cum > mkt_ma12).map({True: 'bull', False: 'bear'})
    )
    # 数值化关键列
    for col in ['总市值', 'bias_20', '成交额std_10', '市盈率倒数', '市净率倒数',
                '最高价', '最低价', '收盘价', 'MACD', 'DIF', 'DEA',
                '涨跌幅_20', '涨跌幅std_20', '成交额']:
        if col in df.columns:
            df[col] = safe_float(df[col])
    return df


def apply_base_filters(df):
    df = df[df['上市至今交易天数'] > 250]
    df = df[~df['股票代码'].str.contains('bj')]
    return df


# ═══════════════════════════════════════════════════════════════════════════
# 缠论因子计算（基于 stock_data.csv 可用列）
# ═══════════════════════════════════════════════════════════════════════════

def compute_chan_factors(df):
    """
    计算 5 个缠论量化因子，对应 quant_factor.md Sections 10-14。

    使用 stock_data.csv 中已有的列（最高价、最低价、收盘价、MACD、DIF、DEA、
    涨跌幅_20、涨跌幅std_20、成交额），通过 groupby 时间序列操作计算。

    返回的因子列：
      chan_bottom_fractal   - 底分型（1=有, 0=无） [Section 12]
      chan_top_fractal      - 顶分型（1=有, 0=无） [Section 12]
      chan_bullish_div      - 底背驰（1=有, 0=无） [Section 10]
      chan_bearish_div      - 顶背驰（1=有, 0=无） [Section 10]
      chan_zs_position      - 中枢相对位置 [Section 11]
      chan_below_zs         - 是否在中枢下方 [Section 11]
      chan_stroke_dir       - 笔方向 (+1向上, -1向下) [Section 13]
      chan_stroke_strength  - 笔强度 [Section 13]
      chan_signal_score     - 综合买卖点得分 [Section 14]
    """
    df = df.sort_values(['股票代码', '交易日期']).copy()

    # ---- 滞后值（每只股票的时间序列） ----
    g = df.groupby('股票代码')
    df['high_l1'] = g['最高价'].shift(1)
    df['high_l2'] = g['最高价'].shift(2)
    df['low_l1'] = g['最低价'].shift(1)
    df['low_l2'] = g['最低价'].shift(2)
    df['close_l1'] = g['收盘价'].shift(1)
    df['close_l2'] = g['收盘价'].shift(2)
    df['macd_l2'] = g['MACD'].shift(2)
    df['volume_l1'] = g['成交额'].shift(1)

    # ═══════════════════════════════════════════
    # 因子 1：分型检测（Fractal, Section 12）
    # 底分型：中间K线(m_l1)是三者中最低的
    # 顶分型：中间K线(m_l1)是三者中最高的
    # K1=high_l2/low_l2, K2=high_l1/low_l1, K3=最高价/最低价
    # ═══════════════════════════════════════════
    df['chan_bottom_fractal'] = (
        (df['high_l1'] < df['high_l2']) &
        (df['high_l1'] < df['最高价']) &
        (df['low_l1'] < df['low_l2']) &
        (df['low_l1'] < df['最低价'])
    ).astype(int)

    df['chan_top_fractal'] = (
        (df['high_l1'] > df['high_l2']) &
        (df['high_l1'] > df['最高价']) &
        (df['low_l1'] > df['low_l2']) &
        (df['low_l1'] > df['最低价'])
    ).astype(int)

    # ═══════════════════════════════════════════
    # 因子 2：背驰检测（Divergence, Section 10）
    # 底背驰：价格下跌但MACD动能改善
    #   close < close_{t-2} AND MACD > MACD_{t-2}
    # 顶背驰：价格上涨但MACD动能衰竭
    #   close > close_{t-2} AND MACD < MACD_{t-2}
    # ═══════════════════════════════════════════
    df['chan_bullish_div'] = (
        (df['收盘价'] < df['close_l2']) &
        (df['MACD'] > df['macd_l2'])
    ).astype(int)

    df['chan_bearish_div'] = (
        (df['收盘价'] > df['close_l2']) &
        (df['MACD'] < df['macd_l2'])
    ).astype(int)

    # 背驰强度（仅用于有背驰的股票）
    denom = np.abs(df['收盘价'] / (df['close_l2'] + 1e-8) - 1) + 1e-8
    df['chan_div_strength'] = (
        np.abs(df['MACD'] - df['macd_l2']) / denom
    )
    df['chan_div_strength'] = df['chan_div_strength'].clip(0, 100)

    # ═══════════════════════════════════════════
    # 因子 3：中枢位置（Zhongshu Position, Section 11）
    # ZG = min(high_t, high_{t-1}, high_{t-2})
    # ZD = max(low_t, low_{t-1}, low_{t-2})
    # position = (close - ZD) / (ZG - ZD)
    # position < 0 → 中枢下方（潜在买点）
    # position 0~1 → 中枢内部
    # position > 1 → 中枢上方（潜在卖点）
    # ═══════════════════════════════════════════
    df['chan_zg'] = df[['最高价', 'high_l1', 'high_l2']].min(axis=1)
    df['chan_zd'] = df[['最低价', 'low_l1', 'low_l2']].max(axis=1)
    df['chan_zs_valid'] = (df['chan_zg'] > df['chan_zd']).astype(int)

    df['chan_zs_position'] = (
        (df['收盘价'] - df['chan_zd']) / (df['chan_zg'] - df['chan_zd'] + 1e-8)
    )
    df['chan_zs_position'] = df['chan_zs_position'].clip(-1, 2)
    df['chan_below_zs'] = (df['chan_zs_position'] < 0).astype(int)
    df['chan_above_zs'] = (df['chan_zs_position'] > 1).astype(int)
    df['chan_inside_zs'] = (
        (df['chan_zs_position'] >= 0) & (df['chan_zs_position'] <= 1)
    ).astype(int)

    # ═══════════════════════════════════════════
    # 因子 4：笔强度（Stroke Momentum, Section 13）
    # 笔方向 = sign(涨跌幅_20)
    # 笔强度 = abs(涨跌幅_20) / (涨跌幅std_20 + eps)
    # ═══════════════════════════════════════════
    df['chan_stroke_dir'] = np.sign(df['涨跌幅_20'])
    df['chan_stroke_strength'] = (
        np.abs(df['涨跌幅_20']) / (df['涨跌幅std_20'] + 1e-8)
    )
    df['chan_stroke_strength'] = df['chan_stroke_strength'].clip(0, 10)

    # 笔加速：短期涨幅 vs 长期涨幅
    # 如果涨跌幅_20上升但之前下跌，则是向上笔的开始
    df['close_l3'] = g['收盘价'].shift(3)
    df['chan_stroke_accel'] = (
        (df['收盘价'] - df['close_l1']) / (df['close_l1'] + 1e-8)
        - (df['close_l1'] - df['close_l3']) / (df['close_l3'] + 1e-8)
    )

    # ═══════════════════════════════════════════
    # 因子 5：综合买卖点信号（Section 14）
    # 一类买点：底分型 + 底背驰 → 最强信号
    # 二类买点：底分型 或 中枢下方 → 中等信号
    # 三类买点：中枢下方 + 笔向上 → 趋势中继
    # ═══════════════════════════════════════════
    df['chan_buy_type1'] = (
        (df['chan_bottom_fractal'] == 1) & (df['chan_bullish_div'] == 1)
    ).astype(int)

    df['chan_buy_type2'] = (
        (df['chan_bottom_fractal'] == 1) | (df['chan_below_zs'] == 1)
    ).astype(int)

    df['chan_buy_type3'] = (
        (df['chan_below_zs'] == 1) & (df['chan_stroke_dir'] > 0)
    ).astype(int)

    # 综合得分（加权）
    df['chan_signal_score'] = (
        3.0 * df['chan_buy_type1'] +   # 一类买点最高权重
        2.0 * df['chan_buy_type2'] +   # 二类买点
        1.0 * df['chan_buy_type3'] -   # 三类买点
        2.0 * df['chan_top_fractal'] - # 顶分型惩罚
        2.0 * df['chan_bearish_div'] - # 顶背驰惩罚
        1.0 * df['chan_above_zs']      # 中枢上方惩罚
    )

    # 清理中间列
    drop_cols = ['high_l1', 'high_l2', 'low_l1', 'low_l2',
                 'close_l1', 'close_l2', 'close_l3', 'macd_l2',
                 'volume_l1', 'chan_zg', 'chan_zd']
    df.drop(columns=[c for c in drop_cols if c in df.columns], inplace=True)

    return df


# ═══════════════════════════════════════════════════════════════════════════
# 策略 A：原版策略（行业估值 + bias反转 + 小市值）
# ═══════════════════════════════════════════════════════════════════════════

def original_strategy(df):
    """原版三步过滤选股策略：行业估值分位 + bias_20过滤 + 成交额波动率过滤 → 选最小市值"""
    df = df.copy()

    # Step 1: 行业估值百分位
    ind_col = '新版申万二级行业名称'
    ind_val = df.groupby([ind_col, '交易日期']).agg(
        med_ep=('市盈率倒数', 'median'),
        med_bp=('市净率倒数', 'median'),
    ).reset_index()

    def calc_val_percentile(grp):
        grp = grp.sort_values('交易日期')
        ep_pct = grp['med_ep'].expanding(min_periods=12).rank(pct=True)
        bp_pct = grp['med_bp'].expanding(min_periods=12).rank(pct=True)
        grp['val_pct'] = (ep_pct.fillna(0.5) + bp_pct.fillna(0.5)) / 2
        return grp

    ind_val = ind_val.groupby(ind_col, group_keys=False).apply(calc_val_percentile)
    df = df.merge(ind_val[[ind_col, '交易日期', 'val_pct']],
                  on=[ind_col, '交易日期'], how='left')
    df['val_pct'] = df['val_pct'].fillna(0.5)
    df = df[df['val_pct'] < 0.68]  # 剔除高估值行业TOP 32%

    # Step 2: bias_20 过滤（股价偏离MA20过高）
    cutoff = df.groupby('交易日期')['bias_20'].transform(lambda x: x.quantile(0.52))
    df = df[df['bias_20'] < cutoff]

    # Step 3: 成交额波动过滤（排除异常交易）
    vol_cutoff = df.groupby('交易日期')['成交额std_10'].transform(lambda x: x.quantile(0.78))
    df = df[df['成交额std_10'] < vol_cutoff]

    # 排名因子：总市值（越小越好）
    df['因子'] = df['总市值']
    return df


# ═══════════════════════════════════════════════════════════════════════════
# 策略 B：缠论增强策略
#
# 在原有三步过滤基础上，融入缠论因子：
#   - 中枢位置过滤（Section 11）：保留中枢下方或内部的股票
#   - 背驰过滤（Section 10）：排除顶背驰严重的股票
#   - 复合排名：市值 + Chan 综合得分
# ═══════════════════════════════════════════════════════════════════════════

def chan_enhanced_strategy(df):
    """
    缠论增强选股策略。

    与 quant_factor.md Sections 10-14 对应：
      - Section 10: 背驰因子 → chan_bullish_div / chan_bearish_div
      - Section 11: 中枢位置因子 → chan_zs_position / chan_below_zs
      - Section 12: 分型因子 → chan_bottom_fractal / chan_top_fractal
      - Section 13: 笔强度因子 → chan_stroke_dir / chan_stroke_strength
      - Section 14: 买卖点信号 → chan_signal_score

    策略逻辑（缠论视角）：
      缠论认为最优买点出现在"下跌 + 底背驰 + 中枢下方"的结构末端。
      但 A 股小市值效应极强（原版累积净值 5000x+），缠论因子不应
      替代市值排名，而应作为**负向排除 + 正向筛选**的辅助层。

      本策略：
        1. 保留原版三步过滤（行业估值 + bias_20 + 成交额波动）
        2. 缠论负向排除：剔除同时满足 中枢上方+顶背驰+顶分型 的最差信号
        3. 缠论正向权重：在市值排名中，给 Chan 积极信号最多 10% 的排名加成
           （相当于在同等市值下，优先选择缠论结构更好的股票）
    """
    df = df.copy()

    # === 缠论因子计算 ===
    df = compute_chan_factors(df)

    # === 原有三步过滤 ===
    ind_col = '新版申万二级行业名称'
    ind_val = df.groupby([ind_col, '交易日期']).agg(
        med_ep=('市盈率倒数', 'median'),
        med_bp=('市净率倒数', 'median'),
    ).reset_index()

    def calc_val_percentile(grp):
        grp = grp.sort_values('交易日期')
        ep_pct = grp['med_ep'].expanding(min_periods=12).rank(pct=True)
        bp_pct = grp['med_bp'].expanding(min_periods=12).rank(pct=True)
        grp['val_pct'] = (ep_pct.fillna(0.5) + bp_pct.fillna(0.5)) / 2
        return grp

    ind_val = ind_val.groupby(ind_col, group_keys=False).apply(calc_val_percentile)
    df = df.merge(ind_val[[ind_col, '交易日期', 'val_pct']],
                  on=[ind_col, '交易日期'], how='left')
    df['val_pct'] = df['val_pct'].fillna(0.5)
    df = df[df['val_pct'] < 0.68]

    # Step 2: bias_20 过滤
    cutoff = df.groupby('交易日期')['bias_20'].transform(lambda x: x.quantile(0.52))
    df = df[df['bias_20'] < cutoff]

    # Step 3: 成交额波动过滤
    vol_cutoff = df.groupby('交易日期')['成交额std_10'].transform(lambda x: x.quantile(0.78))
    df = df[df['成交额std_10'] < vol_cutoff]

    # === Step 4: 缠论负向排除层 ===
    # 缠论 Section 10 + 11 + 12: 中枢上方 + 顶背驰 + 顶分型 = 三重确认强卖点
    # 三者同时出现是缠论中最明确的卖点信号。月线数据中出现极少（<1%），排除成本极低。
    # 缠论理论：中枢上方代表多头主导但已到阻力区，顶背驰代表动能衰竭，
    #           顶分型代表局部见顶——三重确认后不应买入。
    strong_sell_triple = (
        (df['chan_above_zs'] == 1) &
        (df['chan_bearish_div'] == 1) &
        (df['chan_top_fractal'] == 1)
    )
    n_excluded = strong_sell_triple.sum()
    df = df[~strong_sell_triple]

    # === 市值排名（主体） + 缠论边际加成（辅助，3%） ===
    # 市值排名（1 = 最小，lower = better）
    df['rank_size'] = df.groupby('交易日期')['总市值'].rank(ascending=True)

    # 缠论正向得分归一化
    df['chan_signal_norm'] = df['chan_signal_score'].clip(-8, 8) / 8.0

    # 最终排名 = 市值排名 * (1 - 0.03 * chan_signal_norm)
    # Chan 信号最好：市值排名打 97 折（轻微优先）
    # Chan 信号最差：市值排名打 103 折（轻微惩罚）
    # Chan 信号中性：市值排名不变
    # 3% 的权重确保 Chan 仅在几乎同市值的股票之间起 tiebreaker 作用
    df['因子'] = df['rank_size'] * (1.0 - 0.03 * df['chan_signal_norm'])

    return df


# ═══════════════════════════════════════════════════════════════════════════
# 策略 C：纯缠论因子策略（无原始过滤，仅用于对比缠论因子有效性）
# ═══════════════════════════════════════════════════════════════════════════

def chan_only_strategy(df):
    """
    纯缠论因子策略 -- 无行业估值/bias/成交额过滤。
    仅使用缠论因子进行过滤和排名，用于单独评估缠论因子的有效性。

    注意：A 股小市值效应极强，纯缠论策略如完全不考虑市值
    会大幅跑输。此处使用市值作为次要 tiebreaker（30%权重）。
    """
    df = df.copy()
    df = compute_chan_factors(df)

    # 缠论过滤层
    df = df[df['chan_bearish_div'] == 0]        # 无顶背驰
    df = df[df['chan_top_fractal'] == 0]        # 无顶分型
    df = df[df['chan_zs_valid'] == 1]           # 有有效中枢
    df = df[df['chan_above_zs'] == 0]           # 不在中枢上方

    # 缠论排名为主（70%），市值为辅（30%）
    df['rank_chan'] = df.groupby('交易日期')['chan_signal_score'].rank(ascending=False)
    df['rank_size'] = df.groupby('交易日期')['总市值'].rank(ascending=True)
    df['因子'] = 0.70 * df['rank_chan'] + 0.30 * df['rank_size']
    return df


# ═══════════════════════════════════════════════════════════════════════════
# 策略 D：Method A — 日线缠论流水线 → 月度聚合 (v2.0)
#
# 与 v1.1 (chan_enhanced_strategy) 的核心区别：
#   v1.1 使用月度频率的代理因子（3-K线分型、MACD bar 对比、3-bar中枢）
#   v2.0 使用 chan_monthly_factor_builder.py 从日线数据跑完整流水线后聚合
#       （真实分型→笔→线段→中枢→背驰→买卖点）
#
# 策略逻辑（遵循 PM 建议）：
#   缠论因子与小市值因子协同而非互斥 — 在小市值桶内用缠论因子排序
# ═══════════════════════════════════════════════════════════════════════════

METHOD_A_FACTOR_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '.cache', 'chan_factors_v2', 'chan_factors_500.csv'
)


def load_method_a_factors(df, factor_path=METHOD_A_FACTOR_PATH):
    """加载并合并 Method A 日线流水线聚合的缠论因子"""
    if not os.path.exists(factor_path):
        print(f"[Method A] 因子文件不存在: {factor_path}，回退到代理因子")
        return compute_chan_factors(df)

    chan_df = pd.read_csv(factor_path, encoding='gbk')
    chan_df['交易日期'] = pd.to_datetime(chan_df['交易日期'])
    # 重命名 Method A 因子列以避免与代理因子冲突
    ma_cols = {
        'chan_top_fractal': 'ma_top_fractal',
        'chan_bottom_fractal': 'ma_bottom_fractal',
        'chan_fractal_ratio': 'ma_fractal_ratio',
        'chan_stroke_dir': 'ma_stroke_dir',
        'chan_stroke_count': 'ma_stroke_count',
        'chan_stroke_strength': 'ma_stroke_strength',
        'chan_zhongshu_count': 'ma_zhongshu_count',
        'chan_zhongshu_position': 'ma_zhongshu_position',
        'chan_zhongshu_width': 'ma_zhongshu_width',
        'chan_top_div': 'ma_top_div',
        'chan_bottom_div': 'ma_bottom_div',
        'chan_div_signal': 'ma_div_signal',
        'chan_buy_signals': 'ma_buy_signals',
        'chan_sell_signals': 'ma_sell_signals',
        'chan_segment_count': 'ma_segment_count',
    }
    chan_df = chan_df.rename(columns=ma_cols)
    # 只保留需要的列
    merge_cols = ['交易日期', '股票代码'] + list(ma_cols.values())
    chan_df = chan_df[[c for c in merge_cols if c in chan_df.columns]]

    df = df.merge(chan_df, on=['交易日期', '股票代码'], how='left')
    # 缺失因子填充为中性值
    for col in ma_cols.values():
        if col in df.columns:
            if col in ('ma_fractal_ratio',):
                df[col] = df[col].fillna(0.5)
            elif col in ('ma_stroke_dir', 'ma_div_signal', 'ma_zhongshu_position',
                         'ma_stroke_strength', 'ma_zhongshu_width'):
                df[col] = df[col].fillna(0.0)
            else:
                df[col] = df[col].fillna(0)
    return df


def method_a_strategy(df, factor_path=METHOD_A_FACTOR_PATH):
    """
    Method A 缠论策略 (v2.0) — 日线流水线 → 月度因子。

    PM 建议：缠论因子应与小市值因子协同而非互斥。
    实现方式：在小市值桶内用缠论因子排序。
    """
    df = df.copy()

    # 加载 Method A 因子
    df = load_method_a_factors(df, factor_path)

    # === 原有三步过滤（与原版相同） ===
    ind_col = '新版申万二级行业名称'
    ind_val = df.groupby([ind_col, '交易日期']).agg(
        med_ep=('市盈率倒数', 'median'),
        med_bp=('市净率倒数', 'median'),
    ).reset_index()

    def calc_val_percentile(grp):
        grp = grp.sort_values('交易日期')
        ep_pct = grp['med_ep'].expanding(min_periods=12).rank(pct=True)
        bp_pct = grp['med_bp'].expanding(min_periods=12).rank(pct=True)
        grp['val_pct'] = (ep_pct.fillna(0.5) + bp_pct.fillna(0.5)) / 2
        return grp

    ind_val = ind_val.groupby(ind_col, group_keys=False).apply(calc_val_percentile)
    df = df.merge(ind_val[[ind_col, '交易日期', 'val_pct']],
                  on=[ind_col, '交易日期'], how='left')
    df['val_pct'] = df['val_pct'].fillna(0.5)
    df = df[df['val_pct'] < 0.68]

    cutoff = df.groupby('交易日期')['bias_20'].transform(lambda x: x.quantile(0.52))
    df = df[df['bias_20'] < cutoff]

    vol_cutoff = df.groupby('交易日期')['成交额std_10'].transform(lambda x: x.quantile(0.78))
    df = df[df['成交额std_10'] < vol_cutoff]

    # === Method A 缠论过滤层 ===
    # 使用真实日线流水线因子进行负向排除
    # 顶背驰 + 中枢上方 + 卖点信号 > 买点信号 → 排除
    if 'ma_div_signal' in df.columns and 'ma_zhongshu_position' in df.columns:
        strong_sell = (
            (df['ma_div_signal'] == -1) &
            (df['ma_zhongshu_position'] > 0.5) &
            (df['ma_sell_signals'] > df['ma_buy_signals'])
        )
        df = df[~strong_sell]

    # === Method A 综合得分 ===
    # 底分型 + 底背驰 + 中枢下方 = 积极信号
    # 顶分型 + 顶背驰 + 中枢上方 = 消极信号
    df['ma_score'] = 0.0
    if 'ma_bottom_fractal' in df.columns:
        df['ma_score'] += df['ma_bottom_fractal'] * 1.0
    if 'ma_top_fractal' in df.columns:
        df['ma_score'] -= df['ma_top_fractal'] * 1.0
    if 'ma_bottom_div' in df.columns:
        df['ma_score'] += df['ma_bottom_div'] * 3.0
    if 'ma_top_div' in df.columns:
        df['ma_score'] -= df['ma_top_div'] * 3.0
    if 'ma_buy_signals' in df.columns:
        df['ma_score'] += df['ma_buy_signals'] * 2.0
    if 'ma_sell_signals' in df.columns:
        df['ma_score'] -= df['ma_sell_signals'] * 2.0
    if 'ma_zhongshu_position' in df.columns:
        df['ma_score'] += (df['ma_zhongshu_position'] < 0).astype(int) * 1.5
        df['ma_score'] -= (df['ma_zhongshu_position'] > 0.5).astype(int) * 1.5

    # === 排名：市值为主，Method A 缠论为辅（5% tilt） ===
    df['rank_size'] = df.groupby('交易日期')['总市值'].rank(ascending=True)
    df['ma_score_norm'] = df['ma_score'].clip(-10, 10) / 10.0
    df['因子'] = df['rank_size'] * (1.0 - 0.05 * df['ma_score_norm'])

    return df


# ═══════════════════════════════════════════════════════════════════════════
# 通用：选股 + 止盈 + 回测评估
# ═══════════════════════════════════════════════════════════════════════════

def select_and_backtest(df, strategy_name="strategy"):
    """对已打好因子分的 df 进行选股和回测"""
    df = df.copy()

    # 解析下周期涨跌幅
    def parse_returns(x):
        if isinstance(x, str):
            try:
                return ast.literal_eval(x)
            except (ValueError, SyntaxError):
                return []
        return x if isinstance(x, list) else []

    df['下周期每天涨跌幅'] = df['下周期每天涨跌幅'].apply(parse_returns)

    # 排名选股（因子值越低越好，取前 select_stock_num 只）
    df['排名'] = df.groupby('交易日期')['因子'].rank(ascending=True)
    df = df[df['排名'] <= select_stock_num]

    df['股票代码'] = df['股票代码'].astype(str) + ' '
    df['股票名称'] = df['股票名称'].astype(str) + ' '

    def apply_take_profit(daily_returns, tp_pct):
        cumret = 1.0
        result = []
        triggered = False
        for r in daily_returns:
            if triggered:
                result.append(0.0)
                continue
            cumret *= (1 + r)
            result.append(r)
            if cumret - 1 > tp_pct:
                triggered = True
                result[-1] = result[-1] - sell_cost
        return result, triggered

    group = df.groupby('交易日期')
    select_stock = pd.DataFrame()
    select_stock['买入股票代码'] = group['股票代码'].sum()
    select_stock['买入股票名称'] = group['股票名称'].sum()

    period_returns = []
    for date, grp in group:
        regime = grp['市场状态'].iloc[0]
        if regime == 'bull':
            tp, n_stocks = BULL_TP, BULL_N
        else:
            tp, n_stocks = BEAR_TP, BEAR_N

        daily_lists = list(grp['下周期每天涨跌幅'])
        daily_lists = daily_lists[:n_stocks]

        final_rets = []
        for daily_ret in daily_lists:
            if not isinstance(daily_ret, list) or len(daily_ret) == 0:
                final_rets.append(1.0)
                continue
            modified, triggered = apply_take_profit(daily_ret, tp)
            cumret = np.prod([1 + r for r in modified])
            if not triggered:
                cumret *= (1 - sell_cost)
            final_rets.append(cumret)
        portfolio_ret = np.mean(final_rets)
        portfolio_ret *= (1 - c_rate)
        period_returns.append(portfolio_ret - 1)

    select_stock['选股下周期涨跌幅'] = period_returns
    select_stock.reset_index(inplace=True)
    select_stock['资金曲线'] = (select_stock['选股下周期涨跌幅'] + 1).cumprod()
    select_stock['累积净值'] = (select_stock['选股下周期涨跌幅'] + 1).cumprod()

    return select_stock


def strategy_evaluate(select_stock):
    """评估策略表现"""
    results = pd.DataFrame()
    results.loc[0, '累积净值'] = round(select_stock['累积净值'].iloc[-1], 2)

    date_delta = select_stock['交易日期'].iloc[-1] - select_stock['交易日期'].iloc[0]
    days = date_delta.days if hasattr(date_delta, 'days') else 365
    if days > 0:
        annual_return = (select_stock['累积净值'].iloc[-1]) ** (365.0 / days) - 1
    else:
        annual_return = 0
    results.loc[0, '年化收益'] = f"{round(annual_return * 100, 2)}%"

    select_stock['max2here'] = select_stock['累积净值'].expanding().max()
    select_stock['dd2here'] = select_stock['累积净值'] / select_stock['max2here'] - 1
    end_date, max_draw_down = tuple(
        select_stock.sort_values(by=['dd2here']).iloc[0][['交易日期', 'dd2here']]
    )
    start_date = (
        select_stock[select_stock['交易日期'] <= end_date]
        .sort_values(by='累积净值', ascending=False)
        .iloc[0]['交易日期']
    )
    select_stock.drop(['max2here', 'dd2here'], axis=1, inplace=True)
    results.loc[0, '最大回撤'] = format(max_draw_down, '.2%')
    results.loc[0, '最大回撤开始'] = str(start_date)[:10]
    results.loc[0, '最大回撤结束'] = str(end_date)[:10]
    results.loc[0, '年化收益/回撤比'] = (
        round(annual_return / abs(max_draw_down), 2) if max_draw_down != 0 else 0
    )
    return results.T


# ═══════════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════════

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'compare'
    if mode.startswith('--mode'):
        mode = sys.argv[2] if len(sys.argv) > 2 else 'compare'

    print("=" * 75)
    print("  缠论 (Chan Theory) 因子增强选股策略 — 对比分析")
    print("  对应 quant_factor.md Sections 10-14: 背驰/中枢/分型/笔强度/买卖点")
    print("=" * 75)

    df_full = load_data()
    df_full = apply_base_filters(df_full)

    strategies = {}
    eval_results = {}

    if mode in ('original', 'compare'):
        print("\n>>> [策略A] 原版策略: 行业估值 + bias反转 + 小市值")
        df_orig = original_strategy(df_full.copy())
        result_orig = select_and_backtest(df_orig, "原版策略")
        result_orig.to_csv('选股策略详情_原版.csv', encoding='gbk', index=False)
        eval_orig = strategy_evaluate(result_orig)
        print("\n[原版策略评估]")
        print(eval_orig.to_string())
        strategies['原版策略'] = result_orig
        eval_results['原版策略'] = eval_orig

    if mode in ('chan', 'compare'):
        print("\n>>> [策略B] 缠论增强策略 (v1.1): 原有过滤 + 缠论代理因子 + 复合排名")
        df_chan = chan_enhanced_strategy(df_full.copy())
        result_chan = select_and_backtest(df_chan, "缠论增强策略")
        result_chan.to_csv('选股策略详情_缠论增强.csv', encoding='gbk', index=False)
        eval_chan = strategy_evaluate(result_chan)
        print("\n[缠论增强策略评估]")
        print(eval_chan.to_string())
        strategies['缠论增强'] = result_chan
        eval_results['缠论增强'] = eval_chan

        print("\n>>> [策略C] 纯缠论策略 (v1.2): 仅缠论因子（无行业/bias/成交额过滤）")
        df_chan_only = chan_only_strategy(df_full.copy())
        result_chan_only = select_and_backtest(df_chan_only, "纯缠论策略")
        result_chan_only.to_csv('选股策略详情_纯缠论.csv', encoding='gbk', index=False)
        eval_chan_only = strategy_evaluate(result_chan_only)
        print("\n[纯缠论策略评估]")
        print(eval_chan_only.to_string())
        strategies['纯缠论'] = result_chan_only
        eval_results['纯缠论'] = eval_chan_only

    if mode in ('method_a', 'compare'):
        print("\n>>> [策略D] Method A (v2.0): 日线缠论流水线 → 月度因子 + 小市值协同")
        df_ma = method_a_strategy(df_full.copy())
        result_ma = select_and_backtest(df_ma, "Method A策略")
        result_ma.to_csv('选股策略详情_MethodA.csv', encoding='gbk', index=False)
        eval_ma = strategy_evaluate(result_ma)
        print("\n[Method A 策略评估]")
        print(eval_ma.to_string())
        strategies['Method A'] = result_ma
        eval_results['Method A'] = eval_ma

    if mode == 'compare':
        print("\n" + "=" * 75)
        print("  策略对比分析")
        print("=" * 75)

        strategy_names = ['原版策略', '缠论增强', '纯缠论']
        has_ma = 'Method A' in eval_results
        if has_ma:
            strategy_names.append('Method A')

        # 提取指标
        def get_metric(eval_res, name, metric):
            return eval_res[name].loc[metric].values[0]

        metrics = {}
        for name in strategy_names:
            metrics[name] = {
                'cumret': get_metric(eval_results, name, '累积净值'),
                'ann_ret': get_metric(eval_results, name, '年化收益'),
                'max_dd': get_metric(eval_results, name, '最大回撤'),
                'calmar': get_metric(eval_results, name, '年化收益/回撤比'),
            }

        # Print comparison table
        header = f"{'指标':<20}" + "".join(f"{n:>18}" for n in strategy_names)
        print(f"\n{header}")
        print("-" * (20 + 18 * len(strategy_names)))
        print(f"{'累积净值':<20}" + "".join(f"{metrics[n]['cumret']:>18.4f}" for n in strategy_names))
        print(f"{'年化收益':<20}" + "".join(f"{metrics[n]['ann_ret']:>18}" for n in strategy_names))
        print(f"{'最大回撤':<20}" + "".join(f"{metrics[n]['max_dd']:>18}" for n in strategy_names))
        print(f"{'收益/回撤比':<20}" + "".join(f"{metrics[n]['calmar']:>18}" for n in strategy_names))

        # 相对改善
        orig_cumret = metrics['原版策略']['cumret']
        if orig_cumret:
            for name in strategy_names[1:]:
                ratio = metrics[name]['cumret'] / orig_cumret - 1
                print(f"\n  {name} vs 原版: 累积净值 {ratio:+.2%}")

        # 月度胜率对比
        print(f"\n[月度胜率]")
        for name in strategy_names:
            win_rate = (strategies[name]['选股下周期涨跌幅'] > 0).mean()
            print(f"  {name}: {win_rate:.2%}")

        # 相关性
        print(f"\n[策略相关性]")
        merged_all = None
        for i, name in enumerate(strategy_names):
            s = strategies[name][['交易日期', '选股下周期涨跌幅']].copy()
            s.columns = ['交易日期', name]
            if merged_all is None:
                merged_all = s
            else:
                merged_all = pd.merge(merged_all, s, on='交易日期')
        corr_matrix = merged_all[[n for n in strategy_names]].corr()
        print(corr_matrix.to_string())

        # 超额收益统计
        for name in strategy_names[1:]:
            excess = merged_all[name] - merged_all['原版策略']
            win_pct = (excess > 0).mean() * 100
            print(f"\n[{name}跑赢原版]: {(excess > 0).sum()}/{len(excess)} 月 ({win_pct:.1f}%)")
            print(f"  平均超额: {excess.mean()*100:.2f}%")

        # 结论
        print(f"\n[结论]")
        for name in strategy_names[1:]:
            if metrics[name]['cumret'] > orig_cumret:
                print(f"  ✅ {name} 累积净值 ({metrics[name]['cumret']:.4f}) > 原版 ({orig_cumret:.4f})")
            else:
                print(f"  ❌ {name} 累积净值 ({metrics[name]['cumret']:.4f}) < 原版 ({orig_cumret:.4f})")
        if 'Method A' not in eval_results:
            print(f"     原因分析: A股小市值效应极强（20年5000x+），缠论因子无法克服市值排序主导权")

        # ── 子周期分析 ──
        print(f"\n[子周期分析：资金曲线牛市 vs 熊市]")
        regime_stats = {}
        for name in strategy_names:
            s = strategies[name].copy()
            s['cum_ret'] = (1 + s['选股下周期涨跌幅']).cumprod()
            s['ma12'] = s['cum_ret'].rolling(12, min_periods=1).mean()
            s['regime'] = np.where(s['cum_ret'] > s['ma12'], 'bull', 'bear')
            for regime in ['bull', 'bear']:
                sub = s[s['regime'] == regime]
                if len(sub) > 0:
                    sub_ret = sub['选股下周期涨跌幅']
                    annual_ret = (1 + sub_ret.mean()) ** 12 - 1 if sub_ret.mean() > -1 else -1
                    key = f"{name}_{regime}"
                    regime_stats[key] = {
                        'months': len(sub),
                        'win_rate': (sub_ret > 0).mean(),
                        'monthly_ret': sub_ret.mean(),
                        'annual_ret': annual_ret
                    }

        for name in strategy_names:
            print(f"  {name}:")
            for regime in ['bull', 'bear']:
                key = f"{name}_{regime}"
                if key in regime_stats:
                    rs = regime_stats[key]
                    print(f"    {regime}: {rs['months']}月, 胜率 {rs['win_rate']:.1%}, "
                          f"月均收益 {rs['monthly_ret']:.2%}, 年化 {rs['annual_ret']:.1%}")

        # ── 滚动 12 月回撤对比 ──
        print(f"\n[滚动 12 月最大回撤对比]")
        for name in strategy_names:
            s = strategies[name]
            rets = s['选股下周期涨跌幅'].values
            rolling_max_dd = []
            for i in range(11, len(rets)):
                window = rets[i-11:i+1]
                cum = (1 + window).cumprod()
                peak = np.maximum.accumulate(cum)
                dd = (cum / peak - 1).min()
                rolling_max_dd.append(dd)
            if rolling_max_dd:
                avg_dd = np.mean(rolling_max_dd)
                max_dd_12m = np.min(rolling_max_dd)
                print(f"  {name}: 12月平均最大回撤 {avg_dd:.2%}, 12月极端回撤 {max_dd_12m:.2%}")

        # ── Chan 因子 IC 分析 ──
        print(f"\n[Chan 因子 IC 分析（Rank IC with 下周期月收益）]")
        df_ic = compute_chan_factors(df_full.copy())
        # Calculate next-month return for each stock
        df_ic = df_ic.sort_values(['股票代码', '交易日期'])
        # 下周期涨跌幅是 list，取平均值作为月收益代理
        def parse_avg_ret(x):
            if isinstance(x, str):
                try:
                    lst = ast.literal_eval(x)
                except (ValueError, SyntaxError):
                    return np.nan
            elif isinstance(x, list):
                lst = x
            else:
                return np.nan
            if len(lst) == 0:
                return np.nan
            return np.mean(lst)

        df_ic['next_month_ret'] = df_ic['下周期每天涨跌幅'].apply(parse_avg_ret)

        # Rank IC per cross-section
        ic_records = []
        for date, grp in df_ic.dropna(subset=['next_month_ret']).groupby('交易日期'):
            if len(grp) < 30:
                continue
            for factor_col in ['chan_signal_score', 'chan_bullish_div',
                              'chan_bottom_fractal', 'chan_below_zs',
                              'chan_stroke_strength', 'chan_div_strength']:
                if factor_col not in grp.columns:
                    continue
                valid = grp[[factor_col, 'next_month_ret']].dropna()
                if len(valid) < 30:
                    continue
                ic = valid[factor_col].rank().corr(valid['next_month_ret'].rank())
                ic_records.append({'交易日期': date, 'factor': factor_col, 'IC': ic})

        if ic_records:
            df_ic_stats = pd.DataFrame(ic_records)
            ic_summary = df_ic_stats.groupby('factor')['IC'].agg(['mean', 'std', 'count'])
            ic_summary['IR'] = ic_summary['mean'] / (ic_summary['std'] + 1e-8)
            ic_summary['t_stat'] = ic_summary['mean'] / (ic_summary['std'] / np.sqrt(ic_summary['count']))
            ic_summary['pos_ratio'] = df_ic_stats.groupby('factor')['IC'].apply(lambda x: (x > 0).mean())

            factor_names = {
                'chan_signal_score': '综合买卖点得分',
                'chan_bullish_div': '底背驰信号',
                'chan_bottom_fractal': '底分型信号',
                'chan_below_zs': '中枢下方信号',
                'chan_stroke_strength': '笔强度',
                'chan_div_strength': '背驰强度'
            }
            print(f"  {'因子':<16} {'Mean IC':>8} {'Std IC':>8} {'IR':>8} {'t-stat':>8} {'IC>0':>8}")
            print(f"  {'-'*16} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
            for factor in ic_summary.index:
                name = factor_names.get(factor, factor)
                row = ic_summary.loc[factor]
                print(f"  {name:<16} {row['mean']:>8.4f} {row['std']:>8.4f} "
                      f"{row['IR']:>8.3f} {row['t_stat']:>8.2f} {row['pos_ratio']:>7.1%}")

        # Chan 因子截面统计
        print(f"\n[缠论因子截面统计（最后一期）]")
        df_last_full = compute_chan_factors(df_full.copy())
        df_last = df_last_full[df_last_full['交易日期'] == df_last_full['交易日期'].max()]
        if len(df_last) > 0:
            n = len(df_last)
            print(f"  数据日期: {df_last['交易日期'].iloc[0]}")
            print(f"  有效股票数: {n}")
            print(f"  底分型占比: {df_last['chan_bottom_fractal'].mean()*100:.1f}%")
            print(f"  顶分型占比: {df_last['chan_top_fractal'].mean()*100:.1f}%")
            print(f"  底背驰占比: {df_last['chan_bullish_div'].mean()*100:.1f}%")
            print(f"  顶背驰占比: {df_last['chan_bearish_div'].mean()*100:.1f}%")
            print(f"  中枢下方占比: {df_last['chan_below_zs'].mean()*100:.1f}%")
            print(f"  中枢上方占比: {df_last['chan_above_zs'].mean()*100:.1f}%")
            print(f"  中枢内部占比: {df_last['chan_inside_zs'].mean()*100:.1f}%")
            print(f"  有效中枢占比: {df_last['chan_zs_valid'].mean()*100:.1f}%")
            print(f"  向上笔占比: {(df_last['chan_stroke_dir']>0).mean()*100:.1f}%")
            print(f"  一类买点占比: {df_last['chan_buy_type1'].mean()*100:.1f}%")
            print(f"  二类买点占比: {df_last['chan_buy_type2'].mean()*100:.1f}%")
            print(f"  三类买点占比: {df_last['chan_buy_type3'].mean()*100:.1f}%")
            print(f"  信号得分均值: {df_last['chan_signal_score'].mean():.2f}")

        print("\n" + "=" * 75)

        # 生成可视化图表
        plot_strategy_comparison(strategies, eval_results)

    return strategies, eval_results


# ═══════════════════════════════════════════════════════════════════════════
# 可视化
# ═══════════════════════════════════════════════════════════════════════════

def plot_strategy_comparison(strategies, eval_results, save_path=None):
    if save_path is None:
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '策略对比图表.png')
    """生成策略对比图表：资金曲线 + 回撤 + 月度收益分布"""
    if not strategies:
        return

    strategy_names = list(strategies.keys())
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    color_map = dict(zip(strategy_names, colors[:len(strategy_names)]))

    fig, axes = plt.subplots(3, 1, figsize=(18, 14))
    fig.suptitle('选股策略对比分析', fontsize=16, fontweight='bold', y=0.98)

    # ── Panel 1: 累积净值曲线 ──
    ax1 = axes[0]
    for name in strategy_names:
        s = strategies[name]
        ax1.plot(s['交易日期'], s['累积净值'], color=color_map[name],
                 linewidth=1.2, alpha=0.9, label=name)
    ax1.set_ylabel('累积净值 (log)', fontsize=11)
    ax1.set_title('资金曲线', fontsize=13, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=9, framealpha=0.9)
    ax1.set_yscale('log')
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=1, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)

    # 标注牛市/熊市背景
    for name in strategy_names:
        s = strategies[name].copy()
        if '选股下周期涨跌幅' not in s.columns:
            continue
        s['cum_ret'] = (1 + s['选股下周期涨跌幅']).cumprod()
        s['ma12'] = s['cum_ret'].rolling(12, min_periods=1).mean()
        bear_starts = s[s['cum_ret'] < s['ma12']]
        if len(bear_starts) > 0:
            for date in bear_starts['交易日期']:
                ax1.axvspan(date, date + pd.Timedelta(days=28), color='red', alpha=0.03, lw=0)
        break  # Only plot regime background once

    # ── Panel 2: 回撤曲线 ──
    ax2 = axes[1]
    for name in strategy_names:
        s = strategies[name]
        cum = s['累积净值'].values
        peak = np.maximum.accumulate(cum)
        dd = (cum / peak - 1) * 100
        ax2.fill_between(s['交易日期'], 0, dd, color=color_map[name],
                         alpha=0.35, linewidth=0.8, label=name)
        ax2.plot(s['交易日期'], dd, color=color_map[name],
                 linewidth=0.8, alpha=0.8)
    ax2.set_ylabel('回撤 (%)', fontsize=11)
    ax2.set_title('回撤曲线', fontsize=13, fontweight='bold')
    ax2.legend(loc='lower left', fontsize=9, framealpha=0.9)
    ax2.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    ax2.grid(True, alpha=0.3)

    # 标注最大回撤
    for name in strategy_names:
        s = strategies[name]
        cum = s['累积净值'].values
        peak = np.maximum.accumulate(cum)
        dd = cum / peak - 1
        min_idx = np.argmin(dd)
        ax2.annotate(f'{name}\n{dd[min_idx]:.1%}',
                     xy=(s['交易日期'].iloc[min_idx], dd[min_idx] * 100),
                     fontsize=7, color=color_map[name], alpha=0.8,
                     ha='center', va='top')

    # ── Panel 3: 月度收益分布 ──
    ax3 = axes[2]
    # 合并所有策略收益为统一日期索引
    merged_returns = None
    for name in strategy_names:
        s = strategies[name][['交易日期', '选股下周期涨跌幅']].copy()
        s.columns = ['交易日期', name]
        if merged_returns is None:
            merged_returns = s
        else:
            merged_returns = pd.merge(merged_returns, s, on='交易日期', how='outer')
    merged_returns = merged_returns.dropna()

    # 提取年度
    merged_returns['年份'] = merged_returns['交易日期'].dt.year
    years = sorted(merged_returns['年份'].unique())

    if len(years) > 25:
        # 太多年份时每3年标注一个
        tick_years = years[::3]
    else:
        tick_years = years

    x = np.arange(len(years))
    bar_width = 0.8 / len(strategy_names)

    for i, name in enumerate(strategy_names):
        yearly = merged_returns.groupby('年份')[name].apply(
            lambda x: (1 + x).prod() - 1
        )
        yearly = yearly.reindex(years, fill_value=0)
        offset = (i - len(strategy_names) / 2 + 0.5) * bar_width
        bars = ax3.bar(x + offset, yearly.values * 100, bar_width,
                       color=color_map[name], alpha=0.8, label=name)
        # 标注极端值
        for j, (yr, val) in enumerate(zip(years, yearly.values)):
            if abs(val) > 0.5:
                ax3.annotate(f'{yr}', (x[j] + offset, val * 100),
                            fontsize=5, ha='center', va='bottom' if val > 0 else 'top',
                            rotation=90, alpha=0.6)

    ax3.set_ylabel('年度收益 (%)', fontsize=11)
    ax3.set_title('年度收益对比', fontsize=13, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels([str(y) for y in tick_years], rotation=45, fontsize=8)
    # If we subsampled, hide the other tick labels
    if len(tick_years) < len(years):
        for i, yr in enumerate(years):
            if yr not in tick_years:
                ax3.get_xticklabels()[i].set_visible(False) if i < len(ax3.get_xticklabels()) else None
    ax3.legend(loc='upper left', fontsize=9, framealpha=0.9)
    ax3.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    ax3.grid(True, alpha=0.3, axis='y')

    # 添加指标表
    table_text = "关键指标:\n"
    for name in strategy_names:
        if name in eval_results:
            er = eval_results[name]
            cumret = er.loc['累积净值'].values[0] if '累积净值' in er.index else 'N/A'
            ann_ret = er.loc['年化收益'].values[0] if '年化收益' in er.index else 'N/A'
            max_dd = er.loc['最大回撤'].values[0] if '最大回撤' in er.index else 'N/A'
            table_text += f"\n{name}: 净值={cumret}  年化={ann_ret}  DD={max_dd}"

    fig.text(0.02, 0.01, table_text, fontsize=7, family='monospace',
             verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout(rect=[0, 0.08, 1, 0.95])
    plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"\n[图表已保存] → {save_path}")
    plt.close()


if __name__ == '__main__':
    main()
