# A 股三重滤网研究原型

仅供研究与回测，不构成投资建议。

指标与策略依据：公开资料交叉核对，非原书直引。`source_page` 全为 null。

## 结构

- `elder_indicators/`：框架无关的 pandas/numpy 指标、三重滤网信号、A 股交易规则和风控。
- `market_data/`：AkShare/BaoStock 行情适配、复权双轨、本地 CSV 缓存和周期聚合。
- `strategy_adapters/`：VN.py CTA 策略边界。
- `tests/`：本地手工行情、数值预期和未来数据扰动测试，不访问网络。
- `docs/indicators.yaml`：参数与 A 股市场规则的唯一配置来源。

## 环境

在 WorkBuddy 上级目录建立的 Python 3.13 环境中安装 VN.py 和扩展：

```bash
python3.13 -m venv ../.venv-vnpy
../.venv-vnpy/bin/python -m pip install -e ../vnpy -e ../vnpy_ctastrategy -e ../vnpy_ctabacktester
../.venv-vnpy/bin/python -m pip install -r requirements.txt
```

## 行情下载与缓存

AkShare 为默认数据源。下载会联网，写入 `data/cache/`，并保存请求日期、抓取时间及复权口径元数据。AkShare 提供日线 qfq/raw 和原始 60 分钟行情，60 分钟 qfq 轨由当日 qfq/raw 日收盘比例换算。Baostock 可通过 `market.data_source` 切换，使用其 qfq/raw 周期参数。

日线 `is_st` 状态可通过传入行情 frame 的同名布尔列覆盖板块默认涨跌幅。若行情供应商不提供历史 ST 状态，必须附入经过核实的历史状态列，不能把当前 ST 状态回填到整段历史。

```bash
../.venv-vnpy/bin/python -m market_data.provider \
  --symbol 600519.SH --start-date 2026-10-01 --end-date 2026-11-20
```

若 EastMoney 接口不可用，可使用 AkShare 包中的 Sina 行情接口，不经过 EastMoney：

```bash
../.venv-vnpy/bin/python -m market_data.provider --provider akshare_sina \
  --symbol 600519.SH --start-date 2026-10-01 --end-date 2026-11-20
```

从已缓存行情离线计算并导出信号：

```bash
../.venv-vnpy/bin/python -m market_data.replay --symbol 600519.SH
```

`examples/signals.csv` 和 `examples/signal-validation.html` 是 600519.SH 的长区间验证快照。当前缓存日线覆盖 2022-01-04 15:00 至 2026-11-20 15:00，共 1,182 根。Sina 60 分钟线实际范围为 2024-11-11 14:00 至 2026-11-20 15:00，共 1,970 根，形成 492 个完整交易日；数据源没有返回更早的分钟历史，所以信号最早从 2024-12-12 出现。完整来源范围与抓取时间记录在 `data/cache/600519_SH_metadata.json`。

## 展示层快照

用已有 qfq/raw 缓存、`examples/signals.csv` 和 YAML 配置生成 Lightweight Charts HTML。生成过程不重新下载行情，也不重算信号。HTML 从固定版本的 unpkg CDN 加载图表脚本，打开页面时需要网络访问该静态资源。

```bash
../.venv-vnpy/bin/python -m presentation.build_dashboard \
  --symbol 600519.SH --name 贵州茅台 --output examples/triple-screen.html
```

回放程序读取缓存文件，不会在指标计算期间访问网络。指标使用 qfq OHLCV，订单价和涨跌停校验使用 raw OHLCV。60 分钟线不补造午休/停牌 bar。日线仅由配置要求的完整四根 60 分钟 bar 聚合；周线按 XSHG 交易日历，仅保留完整交易周。

## 测试

```bash
../.venv-vnpy/bin/python -m pytest -q
```

测试仅使用手工 OHLCV fixture。真实行情 E2E 单独执行上面的下载命令，成功时打印四组缓存行数及数据日期/复权元数据。

## 参数与实现范围

指标周期、阈值、时间周期、风险参数从 `docs/indicators.yaml` 的 `params:` 读取。复权、板块/ST 涨跌幅、交易时段、停牌和复牌规则从 `market:` 读取。

实现：`IND-01` EMA、`IND-02` MACD、`IND-03` Force Index、`IND-04` Elder-Ray、`IND-05` Stochastic、`IND-06` RSI、`IND-09` Volume。

未实现清单：`IND-07` Williams %R、`IND-08` 背离分类、`IND-10` OBV、`IND-12` 趋势线/支撑阻力均为 optional，按要求默认跳过；`IND-11` A/D 与 Herrick Payoff Index、`IND-13` K 线/形态均为 skip。原因是规格 status 非 implement，或公式/来源未核实。

目前不实现网络下载以外的自动交易。VN.py CTA 成交价和 A 股撮合限制应在框架回测/执行边界继续验证；信号引擎本身只输出带来源的候选，不假设涨跌停排队成交。
