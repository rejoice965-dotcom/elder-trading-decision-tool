# P1 项目底座选型报告（A 股增量复核）

复核日期：2026-11-20。目标市场按沪深 A 股评估。本阶段只做 GitHub 调研与选型，不 clone 仓库，不实现产品代码。本文更新并取代前版 Jesse 最终选择；**VN.py 底座已于 2026-11-20 23:44 经用户确认，P2 可以开始实现**。

## 结论

**建议底座为 `vnpy/vnpy`，连同其 CTA 策略和 CTA 回测扩展。** VN.py 的 CTA 模块提供多周期策略例子、可外部设置的策略参数，CTA 回测扩展可在 K 线上绘制成交点。核心与两个相关扩展模块的 GitHub license 均为 MIT。A 股行情需由产品侧 AkShare 适配器导入 VN.py 本地数据层，T+1、板块/ST 涨跌停、100 股整手等约束由产品侧策略适配器实施。

在同一信号中组合 60 分钟、日线和周线时，VN.py 的示例证明了多周期策略能力（示例为 5 分钟和 15 分钟），但没有现成的周/日/60 分钟 A 股模板。计划由产品侧从已收盘的 60 分钟线生成日线，再从已收盘日线生成周线。该聚合和 A 股撮合约束是预计的产品侧工作量，不会写入框架仓库。

VN.py 没有查到类似 Freqtrade `lookahead-analysis` 的独立未来函数审计命令。后续用本地 fixture、已收盘 K 线断言和未来数据扰动测试验证信号无前视。

## GitHub 检索

`gh` 不可用（`command -v gh` 无输出），未安装。检索使用 GitHub REST API `curl`。查询返回的是实际 API 结果；仓库字段再通过 `GET /repos/{owner}/{repo}` 核验。Stars 与 push 是 2026-11-20 的快照。

### 策略框架方向

检索命令：

```bash
curl -sS -H 'Accept: application/vnd.github+json' \
  'https://api.github.com/search/repositories?q=China+A-share+quant+backtest+language:python&sort=stars&per_page=20' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('count='+str(d.get('total_count'))); [print(f\"{i['full_name']} | stars={i['stargazers_count']} | pushed={i['pushed_at']} | archived={i['archived']}\") for i in d.get('items',[])]"
```

返回结果：

```text
count=11
rootSunc/CNEquity | stars=1067 | pushed=2026-11-13T21:03:53Z | archived=False
fkchaos/a-share-quant-sim | stars=17 | pushed=2026-10-05T08:14:57Z | archived=False
MisakaMikoto128/china-astock-quant | stars=9 | pushed=2026-05-09T13:12:16Z | archived=False
Jcstack/ashare-ai-analyst | stars=7 | pushed=2026-06-26T15:21:13Z | archived=False
Miluer-tcq/etf-quant-lab | stars=6 | pushed=2026-07-18T04:41:32Z | archived=False
kunboyao-Bo/WorldQuant-101-factors-backtest-Chinese-A-share | stars=4 | pushed=2026-05-15T08:50:17Z | archived=False
Brad-zqh/us-stock-quant | stars=3 | pushed=2026-11-19T21:31:52Z | archived=False
David-Marina/marina-rules | stars=1 | pushed=2026-11-16T02:31:33Z | archived=False
bulala20/quant-trading-course | stars=0 | pushed=2026-08-20T11:59:40Z | archived=False
Wsw-lab/qdata-free-source-quant-research-db | stars=0 | pushed=2026-08-31T15:07:30Z | archived=False
PHM-Audit/astock-mcp-server | stars=0 | pushed=2026-11-18T01:44:42Z | archived=False
```

### 图表库方向

检索命令：

```bash
curl -sS -H 'Accept: application/vnd.github+json' \
  'https://api.github.com/search/repositories?q=javascript+financial+chart+stars:%3E1000&sort=stars&per_page=10' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f\"{i['full_name']} | stars={i['stargazers_count']} | pushed={i['pushed_at']} | archived={i['archived']}\") for i in d.get('items',[])]"
```

返回结果：

```text
tradingview/lightweight-charts | stars=17915 | pushed=2026-11-18T14:48:17Z | archived=False
```

### 指标库方向

检索命令：

```bash
curl -sS -H 'Accept: application/vnd.github+json' \
  'https://api.github.com/search/repositories?q=technical+indicator+library+language:python+stars:%3E100&sort=stars&per_page=10' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f\"{i['full_name']} | stars={i['stargazers_count']} | pushed={i['pushed_at']} | archived={i['archived']}\") for i in d.get('items',[])]"
```

返回结果：

```text
kylejusticemagnuson/pyti | stars=667 | pushed=2026-06-26T17:59:33Z | archived=False
jrmeier/fast-trade | stars=607 | pushed=2026-10-16T04:05:35Z | archived=False
TulipCharts/tulipy | stars=377 | pushed=2021-07-15T16:00:39Z | archived=False
vsaveris/trading-technical-indicators | stars=153 | pushed=2025-11-23T17:26:18Z | archived=False
mr-easy/streaming_indicators | stars=153 | pushed=2026-10-16T17:03:21Z | archived=False
alihaskar/pycharting | stars=120 | pushed=2026-10-27T05:15:20Z | archived=False
TechfaneTechnologies/QtsApp | stars=103 | pushed=2023-02-07T07:20:24Z | archived=False
```

补充依赖的仓库元数据与活跃度：

| 补充项目 | Stars | 最近 push (UTC) | License | 主语言 | Archived | 近 90 天 issue / PR |
|---|---:|---|---|---|---|---:|
| [tradingview/lightweight-charts](https://github.com/tradingview/lightweight-charts) | 17,915 | 2026-11-18 | Apache-2.0 | TypeScript | 否 | 6 / 94 |
| [TA-Lib/ta-lib-python](https://github.com/TA-Lib/ta-lib-python) | 12,426 | 2026-11-11 | BSD-2-Clause | Cython | 否 | 62 / 38 |

## 候选仓库数据

近 90 天活跃度定义为 `2026-08-20` 后更新的 issue 数 / PR 数，使用 GitHub Search Issues API 分开统计。其余字段来自各仓库 REST API。`NOASSERTION` 表示 API 没有识别到 SPDX license，下面会结合仓库 LICENSE 原文判断。

元数据复核命令示例：

```bash
for repo in ricequant/rqalpha vnpy/vnpy edtechre/pybroker; do
  curl -sS -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$repo"
done
```

| 候选 | Stars | 最近 push (UTC) | License | 主语言 | Archived | 近 90 天 issue / PR | A 股适配概况 |
|---|---:|---|---|---|---|---:|---|
| [vnpy/vnpy](https://github.com/vnpy/vnpy) | 46,439 | 2026-11-11 | MIT | Python | 否 | 19 / 44 | 没有内置 AkShare；可把适配数据写入本地数据层，适配成本中等 |
| [ricequant/rqalpha](https://github.com/ricequant/rqalpha) | 6,889 | 2026-10-28 | 自定义许可，商业使用需授权 | Python | 否 | 23 / 36 | 面向中国市场，数据和周线历史 bars API 较完整 |
| [edtechre/pybroker](https://github.com/edtechre/pybroker) | 3,724 | 2026-11-16 | Apache 2.0 + Commons Clause 条款 | Python | 否 | 1 / 66 | README 明列 AkShare 数据源；交易规则需自定义 |
| [jesse-ai/jesse](https://github.com/jesse-ai/jesse) | 8,823 | 2026-11-17 | MIT | Python | 否 | 17 / 33 | 加密市场取向，需自行接入 A 股行情与规则 |
| [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | 57,099 | 2026-11-19 | GPL-3.0 | Python | 否 | 72 / 242 | 加密市场取向，A 股交易时段、T+1 和涨跌停适配成本高 |

VN.py 配套模块元数据也通过 REST API 核实：`vnpy/vnpy_ctastrategy` 为 230 stars、push 2026-10-05、MIT、Python、未归档；`vnpy/vnpy_ctabacktester` 为 99 stars、push 2026-10-05、MIT、Python、未归档；`vnpy/vnpy_chartwizard` 为 22 stars、push 2026-10-05、MIT、Python、未归档。CTA 策略、回测图表模块是推荐组合的一部分。

## 硬约束 A-F 与源码证据

| 候选 | A 多周期 | B 自定义公式 | C K 线信号标注 | D 许可证/活跃/未归档 | E 参数外置 | F A 股行情适配 | 结论 |
|---|---|---|---|---|---|---|---|
| VN.py | `vnpy_ctastrategy/strategies/multi_timeframe_strategy.py` 展示在 15 分钟均线与 5 分钟 RSI 间组合信号；其 `BarGenerator` 可聚合更高周期。项目侧从 60 分钟聚合日线、从完整日线聚合周线 | `CtaTemplate` 为可扩展 Python 策略模板，允许产品策略调用独立 pandas 指标 | `vnpy_ctabacktester/ui/widget.py` 的 `CandleChartDialog.update_trades()` 在 K 线图上添加 `ScatterPlotItem`、方向符号和成交文本 | 核心、CTA 策略和回测扩展均 MIT；push 在 12 个月内；均未归档 | `CtaTemplate.parameters` 与 `update_setting(setting)` 从 setting 更新策略参数 | 可连接 AkShare/本地 CSV 并导入 VN.py 数据库；交易规则在适配层显式约束 | **通过**，周线聚合及 A 股约束由产品侧负责 |
| RQAlpha | 官方测试 `tests/unittest/test_data/test_data_proxy/test_weekly_history_bars.py` 验证 `1w` 与 `1d` 数据 API | Python strategy 和自定义 data source | `rqalpha_mod_sys_analyser/plot/plot.py` 的 open/close 点绘制在收益曲线上，不是 K 线 | LICENSE 原文允许非商业用途依 Apache 2.0；商业用途及法人使用需米筐授权 | 策略参数可由配置传入 | 面向中国市场，数据源/自定义数据文档存在 | C 需另接图表；商用须授权，不作本次默认推荐 |
| PyBroker | README 的 Multiple Time Intervals 示例支持多个区间（列举日/周/月）；A 股 60 分钟要验证并配置 interval | 官方 `Writing Indicators` 和自定义 data source 文档 | 结果可输出交易记录，未发现内置 K 线交易 marker，需接 Lightweight Charts | GitHub API 为 NOASSERTION；LICENSE 含 Commons Clause，限制出售软件/服务 | 提供参数优化，且函数接受参数 | README 明列 AkShare，并可实现自定义数据源；T+1/涨跌停须自定义 | C 和 D 有额外限制，淘汰 |
| Jesse | README 宣称多 timeframe；按 A 股接入仍需行情及日历适配 | Python strategy 可自定义 | 内置交易图展示 orders/trades | MIT、活跃、未归档 | 可扩展策略参数 | 7×24 加密市场撮合，不具 A 股 T+1/涨跌停 | F 成本高，不选 |
| Freqtrade | `@informative` / `merge_informative_pair` | pandas strategy 可定义 | FreqUI 展示交易；不按 deprecated 的 `plot-dataframe` 打分 | GPL-3.0、活跃、未归档 | `IntParameter` 等 | 加密市场取向，交易时段、T+1、涨跌停需重做 | F 成本高且 GPL 影响分发，不选 |

### 关键上游证据

- VN.py 多周期策略示例：[vnpy_ctastrategy/strategies/multi_timeframe_strategy.py](https://github.com/vnpy/vnpy_ctastrategy/blob/main/vnpy_ctastrategy/strategies/multi_timeframe_strategy.py)
- VN.py 策略参数列表与 `update_setting`：[vnpy_ctastrategy/template.py](https://github.com/vnpy/vnpy_ctastrategy/blob/main/vnpy_ctastrategy/template.py)
- VN.py K 线成交点与图表代码：[vnpy_ctabacktester/ui/widget.py](https://github.com/vnpy/vnpy_ctabacktester/blob/main/vnpy_ctabacktester/ui/widget.py)
- VN.py CTA 回测模块 README 说明 GUI 历史回测与参数优化：[vnpy_ctabacktester/README.md](https://github.com/vnpy/vnpy_ctabacktester/blob/main/README.md)
- VN.py CTA 策略模块 README 说明策略开发、回测、优化流程：[vnpy_ctastrategy/README.md](https://github.com/vnpy/vnpy_ctastrategy/blob/main/README.md)
- RQAlpha 周线 history bars 测试：[test_weekly_history_bars.py](https://github.com/ricequant/rqalpha/blob/master/tests/unittest/test_data/test_data_proxy/test_weekly_history_bars.py)
- RQAlpha 自定义许可原文：[LICENSE](https://github.com/ricequant/rqalpha/blob/master/LICENSE)
- PyBroker 文档列出的 AkShare、multi-interval、custom data source：[README.md](https://github.com/edtechre/pybroker/blob/master/README.md)
- PyBroker 许可条款：[LICENSE](https://github.com/edtechre/pybroker/blob/master/LICENSE)

VN.py 示例具体演示的是 5/15 分钟，不是周/日/60 分钟。推荐方案的周、日、60 分钟输入契约由产品侧 `market_data/bars.py` 完成，因此 P2 必须专门测试周期封口、午休断档、周线收盘和停牌缺失，不能把示例误述为已有完整 A 股三周期模板。

## 许可证影响

- **MIT**（VN.py 核心及 CTA 扩展）允许商业和非商业修改、再分发，需保留版权与许可文本。
- **GPL-3.0**（Freqtrade）允许商用，但分发 fork 衍生作品时通常需按 GPL 提供相应源码；若产品闭源分发会冲突。
- **RQAlpha 自定义 LICENSE**：非商业使用依 Apache 2.0 条件；商业用途的个人和法人使用需先取得米筐授权。不能把它按普通 Apache 2.0 处理。
- **PyBroker Apache 2.0 + Commons Clause**：仓库 LICENSE 增加 Commons Clause 限制，包含出售软件/服务的限制。GitHub API 未识别 SPDX，不能只根据 README 的依赖说明判定可商用。

## 七维度评分

七维度覆盖硬约束，并把 A 股适配成本设为最高权重。每项 1-5 分，权重合计 100%；加权总分为 `sum(分数 × 权重) / 5`。分数是针对本项目路线的工程适配评估。A-F 硬约束未通过的候选不因总分进入最终推荐。

| 维度 | 权重 |
|---|---:|
| 多时间框架 | 15% |
| 自定义指标 / pandas 适配 | 10% |
| K 线信号呈现 | 15% |
| 回测能力 | 15% |
| 活跃度 | 10% |
| 许可证与二次开发成本 | 15% |
| A 股数据与交易规则适配成本 | 20% |

| 候选 | 多周期 | 指标 | K 线 | 回测 | 活跃 | 许可证 | A 股适配 | 加权总分 | 硬约束结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| VN.py | 4 | 5 | 5 | 4 | 5 | 5 | 4 | **90** | 通过，行情和交易规则由适配层补足 |
| RQAlpha | 5 | 5 | 2 | 5 | 4 | 1 | 5 | **77** | 授权与 K 线图表成本不满足默认条件 |
| Jesse | 5 | 4 | 4 | 4 | 4 | 5 | 1 | **74** | F 适配成本高 |
| PyBroker | 4 | 5 | 2 | 5 | 5 | 1 | 4 | **72** | Commons Clause 与 K 线 marker 需额外处理 |
| Freqtrade | 5 | 5 | 5 | 5 | 5 | 1 | 1 | **72** | A 股撮合适配成本高，GPL 需承担传染性 |

## 推荐与淘汰

推荐 VN.py。它在本次候选中同时具备 MIT 许可、活跃维护、多周期策略扩展、策略参数注入和回测 K 线成交点，且允许把框架与 A 股行情接入分开。AkShare 行情会缓存到本地，再通过 VN.py 数据库接口供 CTA 回测和图表读取；纯指标测试只用手工 OHLCV。缺点是 T+1、涨跌停、板块/ST 分类并非本次证据确认的框架内置能力，需在产品策略适配层实现并单测，回测也不模拟所有排队成交细节。

- **RQAlpha**：有周线历史 bars 和中国市场能力，但许可证将商业使用与法人使用置于米筐授权条件下，且默认分析图不是 K 线成交 marker。
- **PyBroker**：AkShare 和多区间数据源契合，但 60 分钟三周期需增测，LICENSE 含 Commons Clause，且没有确认 K 线交易 marker。
- **Jesse**：MIT 和图表能力较好，但加密框架的交易时段、T+1、涨跌停与 A 股不符，适配成本最高之一。
- **Freqtrade**：多周期和未来函数分析工具强，但其 GPL-3.0 对分发 fork 衍生产品有开源义务，且面向加密市场，A 股适配成本高。

## 落地信息

- 建议仓库：`vnpy/vnpy`，由独立 CTA 策略和回测扩展提供策略入口与回测图表。
- 完整 clone 命令：`git clone https://github.com/vnpy/vnpy.git /Users/kaixin/WorkBuddy/2026-11-20-21-16-17/vnpy`
- 本地依赖目录：`/Users/kaixin/WorkBuddy/2026-11-20-21-16-17/vnpy`
- 运行时前提：CTA 扩展 README 标注 Python 3.10–3.13；当前工作区 `python3 --version` 为 3.9.6。P2 需在 WorkBuddy 上级目录建立独立 Python 3.10+ 环境用于 VN.py，避免改写系统 Python。
- CTA 策略扩展：`vnpy_ctastrategy`；回测图表扩展：`vnpy_ctabacktester`。两者分别为独立 MIT 仓库/包，不把它们的代码复制进产品仓库。
- 产品策略适配文件：`/Users/kaixin/WorkBuddy/2026-11-20-21-16-17/codex-elder-trading/strategy_adapters/vnpy_elder_triple_screen.py`，由产品启动入口注册给 CTA 引擎。该文件及所有产品代码均留在 `codex-elder-trading`。
- 产品数据适配路径：`codex-elder-trading/market_data/`；指标与信号：`codex-elder-trading/elder_indicators/`；离线测试：`codex-elder-trading/tests/`。
- AkShare 行情先写入本地缓存，再适配到 VN.py 可读取的数据层；CSV 保留为离线回放格式。端到端数据加载单独运行，单元测试不联网。
- `docs/indicators.yaml` 配置：保留 `params:` 为指标周期与策略参数唯一来源；将 `tf_low` 从 `1h` 明确为 `60m`。将 `market.board_limit_pct` 改为主板、创业板/科创板、北交所、ST 分项表；增加 `trading_sessions` 和 `resume_signal_policy`；前复权 qfq 给指标计算，未复权行情给成交价与涨跌停校验；复牌首根 60 分钟 K 收盘前不生成信号。以上均在用户确认底座后再改 YAML。
- 未来函数工具：VN.py CTA 代码中未发现与 `lookahead-analysis` 同类审计命令。P2/P4 通过只使用已收盘 bars 的代码审查和未来数据扰动测试验证；不声称框架内置了该工具。

## 确认状态（2026-11-20 23:44 用户确认）

用户已确认采用 **VN.py** 底座，P2 可以开始实现。落地信息按上文执行（clone、Python 3.10+ 独立环境、产品侧适配路径、YAML 配置更新、复权双轨与测试边界）。**本报告的选型环节已关闭**，不要再重复选型、重开方案对比或停下来询问底座；RQAlpha / PyBroker 的许可证边界仅作为决策记录保留。
