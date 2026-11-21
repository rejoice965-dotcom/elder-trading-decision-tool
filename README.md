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

在 WorkBuddy 上级目录建立的 Python 3.13 环境中安装 VN.py 和扩展。`requirements.txt` 包含 `exchange-calendars`，代码以 `XSHG` 日历封闭完整周线、补出停牌交易日 whitespace；60 分钟源数据每日按四个收盘时刻检查完整性。

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

回放程序读取缓存文件，指标使用 qfq OHLCV，候选价和涨跌停校验使用 raw OHLCV。交易信号使用数据源提供的日线与 60 分钟线。专项检查用符合配置的四根 60 分钟 K 聚合日线，核对日收盘。周线由日线按 XSHG 交易日历聚合，仅保留完整交易周。

## 测试

```bash
../.venv-vnpy/bin/python -m pytest -q
```

指标与市场规则测试使用手工 OHLCV。展示测试还读取已提交的信号样例。真实行情 E2E 独立运行，下载命令会打印缓存行数和日期、复权元数据。

P4 使用本地缓存跑通读取、展示指标、signals.csv 回放与 HTML 生成：

```bash
./scripts/run_all.sh 600519.SH 贵州茅台
```

A 股数据与规则专项检查：

```bash
../.venv-vnpy/bin/python -m scripts.check_a_share
```

## 展示页面

生成页面的命令见“展示层快照”。在 macOS 可用 `open examples/triple-screen.html` 打开，也可在项目根目录运行 `../.venv-vnpy/bin/python -m http.server --bind 127.0.0.1 8765`，访问 [本地页面](http://127.0.0.1:8765/examples/triple-screen.html)。浏览器需要联网加载固定版本的 Lightweight Charts CDN 脚本，行情数据已写入 HTML。

## 参数与实现范围

指标周期、阈值、时间周期、风险参数从 `docs/indicators.yaml` 的 `params:` 读取。复权、板块/ST 涨跌幅、交易时段、停牌和复牌规则从 `market:` 读取。

实现：`IND-01` EMA、`IND-02` MACD、`IND-03` Force Index、`IND-04` Elder-Ray、`IND-05` Stochastic、`IND-06` RSI、`IND-09` Volume。

未实现清单：`IND-07` Williams %R、`IND-08` 背离分类、`IND-10` OBV、`IND-12` 趋势线/支撑阻力均为 optional，按要求默认跳过；`IND-11` A/D 与 Herrick Payoff Index、`IND-13` K 线/形态均为 skip。原因是规格 status 非 implement，或公式/来源未核实。

## 已知限制与风险

- 当前 Sina 60 分钟历史从 2024-11-11 开始，短于日线历史；周线 EMA/MACD 可用更长日线预热，但信号只能从分钟数据范围开始。
- 缓存没有历史 `is_st` 字段；展示页按 YAML 的板块阈值标注，并明确提示历史 ST 状态不可用。
- SELL 信号可用于研究标记，但 `market.allow_short=false`，仓位面板不会给出开空数量。
- 涨跌停触价显示「可能无法成交」，当前系统不模拟封板排队、滑点、成交概率或真实委托回报。
- P4 抽样发现第 3 重价位引用滞后一日，第 2 重也有规格差异。逐笔复算与复核边界见 [P4 终验证据](docs/P4_ACCEPTANCE.md) 和 [追溯矩阵](docs/TRACEABILITY.md)。
- 单元测试只验证手工 OHLCV 和展示规则；网络源可用性、分钟历史深度会变化。信号和复权序列仍需在目标市场进一步验收。
- 本项目定位为研究与回测工具，不接实盘资金，不构成投资建议。

指标/信号依据统一标注「依据：公开资料交叉核对，非原书直引」。没有电子书，禁止把任何内容表述为书内页码、章节或原文。
