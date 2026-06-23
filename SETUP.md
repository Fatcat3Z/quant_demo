# Quant 量化交易系统 — 从零复现指南

## 环境要求

- **操作系统**: macOS / Linux（Windows 需 WSL2）
- **Python**: 3.8+（推荐 Anaconda `3.8`，`akshare` 对 3.12+ 兼容性差）
- **浏览器**: Google Chrome（用于前端截图验证）
- **磁盘**: ≥5GB（全量 A 股数据 ~800MB CSV，ETF 日线缓存 ~100MB）

## 一、克隆仓库

```bash
git clone <repo-url> quant
cd quant
```

## 二、Python 环境

```bash
# 推荐用 Anaconda 创建独立环境
conda create -n quant python=3.8 -y
conda activate quant

# 安装依赖
pip install flask pandas numpy akshare openpyxl selenium

# 可选（用于数据交叉验证）
pip install tushare yfinance
```

## 三、数据构建（按顺序执行）

### 3.1 A 股月度面板（核心数据，所有选股策略依赖）

```bash
cd stock_trade_demo

# 下载全量 A 股月度数据（约 15-30 分钟，取决于网络）
# 从 2006 年 12 月开始，逐月补充到最新月份
python ../get_stock_info.py --mode supplement --year 2026 --month 6

# 验证
wc -l stock_data.csv
# 预期: ~700,000+ 行
```

### 3.2 指数日线 + ETF 数据

```bash
# 下载 CSI1000 / 创业板 / 科创50 / 纳指 / 标普500 / 黄金 ETF 日线
python index_data.py
# 等价于在 Web 端 POST /api/update_index_data

# 验证缓存文件
ls .cache/csi1000_daily.csv .cache/chinext_daily.csv .cache/star50_daily.csv
ls .cache/nasdaq_daily.csv .cache/sp500_daily.csv
ls .cache/gold_daily.csv
ls .cache/timing_etf/*.csv
```

### 3.3 宏观因子数据（FRED + A 股估值/情绪）

```bash
cd ../scripts

# FRED 宏观（VIX / 利率 / CPI / 利差等）
python download_macro_data.py --skip-yf

# A 股估值 / 情绪（PE-TTM / 国债 10Y / 成交融资）
python fetch_a_share_macro.py

# 合成风险信号 JSON
python build_risk_signals.py

# 验证
ls ../data/fred_VIX.csv ../data/fred_Treasury10Y.csv ../data/fred_FedFundsRate.csv
ls ../data/a_share_macro/pe_ttm.csv ../data/a_share_macro/cn10y.csv
ls ../strategy/risk_signals.json
```

### 3.4 选股策略离线缓存

```bash
cd ../stock_trade_demo

# 构建选股回测缓存（Web 启动时直接加载）
python build_single_factor_cache.py

# 验证
ls .cache/web_cache.pkl
```

### 3.5 择时策略 walk-forward（可选，生成 best_profile）

```bash
cd ../scripts

# 对每个择时策略跑 walk-forward 参数搜索
python walk_forward_train.py --strategy csi1000_timing
python walk_forward_train.py --strategy chinext_timing
python walk_forward_train.py --strategy star50_timing
python walk_forward_train.py --strategy sp500_timing
python walk_forward_train.py --strategy macro_v32_timing

# 黄金择时（新建，暂不需要 walk-forward）
# python walk_forward_train.py --strategy gold_timing

# 验证
ls ../strategy/best_profile_*_timing.json
```

### 3.6 A 股交易日历（可选，前端日期对齐用）

```bash
cd ../stock_trade_demo

python -c "
from index_data import get_a_share_trading_calendar
cal = get_a_share_trading_calendar()
print(f'交易日历: {len(cal)} 天, {cal.min()} ~ {cal.max()}')
"
```

## 四、启动 Web 服务

```bash
cd stock_trade_demo

# 生产启动（前台）
python web_app.py

# 或后台启动
nohup python web_app.py > /tmp/web_app.log 2>&1 &

# 等待就绪（约 30-60 秒，取决于数据量）
until curl -s http://localhost:8080/api/info | grep -q data_max_date; do
  sleep 2
done
echo "服务就绪: http://localhost:8080"
```

### 端口配置

默认端口 `8080`。如需修改，编辑 `web_app.py` 最后的 `app.run(port=8080)`。

## 五、验证各页面

```bash
# 选股页面
curl -s http://localhost:8080/api/info | python3 -m json.tool | head

# A 股择时
curl -s "http://localhost:8080/api/timing/latest_signal?strategy=csi1000_timing" | python3 -m json.tool | head

# 美股择时
curl -s "http://localhost:8080/api/us_timing/latest_signal?strategy=sp500_timing" | python3 -m json.tool | head

# 大宗商品（黄金）
curl -s "http://localhost:8080/api/commodity/latest_signal?strategy=gold_timing" | python3 -m json.tool | head

# 实盘记录
curl -s http://localhost:8080/api/live/records | python3 -m json.tool | head

# 浏览器访问
open http://localhost:8080          # 选股
open http://localhost:8080/timing    # A股择时
open http://localhost:8080/us_timing # 美股择时
open http://localhost:8080/commodity  # 大宗商品
open http://localhost:8080/live      # 实盘记录
```

## 六、数据更新

日常数据更新通过 Web 前端"更新数据"按钮一键完成，或手动 curl：

```bash
# 4 步串跑：指数/ETF → 辅助数据 → 股票月度 → 衍生因子
curl -X POST http://localhost:8080/api/update_data
curl -X POST http://localhost:8080/api/update_index_data
curl -X POST http://localhost:8080/api/update_aux_data
curl -X POST http://localhost:8080/api/update_factor_data

# 查看更新状态
curl -s http://localhost:8080/api/update_data/status | python3 -m json.tool
```

## 七、常见问题

### 7.1 `ModuleNotFoundError: No module named 'flask'`
```bash
pip install flask pandas numpy akshare
```

### 7.2 `akshare` 安装失败（macOS ARM）
```bash
# 可能需要先安装 lxml
pip install lxml
pip install akshare --no-deps
pip install requests beautifulsoup4 html5lib xlrd
```

### 7.3 端口 8080 被占用
```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
kill <PID>
```

### 7.4 前端显示"数据加载失败"
检查 `web_app.py` 启动日志，确认所有数据文件就位：
```bash
ls stock_data.csv                           # A股月度面板
ls .cache/csi1000_daily.csv                 # 指数日线
ls strategy/risk_signals.json               # 风险信号
ls data/fred_VIX.csv                        # 宏观数据
ls ../strategy/risk_signals.json
```

### 7.5 黄金ETF数据未加载
```bash
cd stock_trade_demo
python -c "
from index_data import get_timing_etf_daily
etf = get_timing_etf_daily('gold', force_refetch=True)
print(f'Gold ETF rows: {len(etf)}')
"
```

## 八、项目结构速查

```
quant/
├── stock_trade_demo/           # 主项目
│   ├── web_app.py              # Flask 启动入口
│   ├── backtest.py             # 选股回测引擎
│   ├── index_data.py           # 指数/ETF 数据获取
│   ├── get_stock_info.py       # A 股数据补充
│   ├── strategies/             # 选股策略
│   │   └── registry.py         # 策略注册表（含 COMMODITY_REGISTRY）
│   ├── timing/                 # 择时策略
│   │   ├── strategies.py       # CSI1000/Star50/Chinext/SP500/MacroV32/Gold
│   │   └── backtest.py         # 择时回测引擎
│   ├── web/                    # Web 层
│   │   ├── state.py            # 全局状态 + 缓存管理
│   │   ├── app.py              # Flask app factory + blueprint 注册
│   │   ├── blueprints/         # API 路由（分模块）
│   │   │   ├── pages.py        # 页面渲染
│   │   │   ├── timing_api.py   # A 股择时 API
│   │   │   ├── us_timing_api.py
│   │   │   ├── commodity_api.py # 大宗商品 API（新增）
│   │   │   ├── live_api.py     # 实盘记录 API
│   │   │   └── data_admin_api.py
│   │   └── templates/          # Jinja2 前端
│   │       ├── index.html      # 选股页面
│   │       ├── timing.html     # A 股择时
│   │       ├── us_timing.html  # 美股择时
│   │       ├── commodity.html  # 大宗商品（新增，金色主题）
│   │       └── live.html       # 实盘记录
│   └── .cache/                 # 本地缓存（gitignore）
├── data/                       # 宏观/估值数据
│   ├── fred_*.csv              # FRED 宏观因子
│   └── a_share_macro/          # A 股 PE-TTM / CN10Y / 成交融资
├── scripts/                    # 离线构建脚本
│   ├── build_risk_signals.py   # 风险信号合成
│   ├── walk_forward_train.py   # 择时参数搜索
│   ├── download_macro_data.py  # FRED 数据下载
│   └── fetch_a_share_macro.py  # A 股估值数据抓取
└── strategy/                   # 离线回测产物
    ├── best_profile_*_timing.json  # 最优参数
    └── risk_signals.json       # 风险信号
```
