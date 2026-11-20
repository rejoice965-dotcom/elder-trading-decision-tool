# P1 项目底座选型报告

调研日期：2026-11-20。数据来自 GitHub REST API 与候选仓库 README、文档和源码。本次不 clone 仓库、不改项目代码。

## 结论

选择 [`jesse-ai/jesse`](https://github.com/jesse-ai/jesse) 作为路线 1 原型底座。Jesse 有 MIT 许可证、活跃维护、可在策略中访问多个时间周期的 candles，并提供显示 orders、completed trades 和策略指标的交互图表。自定义计算与产品信号引擎仍放在本项目的独立模块，参数继续由 `docs/indicators.yaml` 读取。Jesse 文档没有发现与 Freqtrade `lookahead-analysis` 同类的独立审计命令，P2/P4 需单独验证未来数据。

## 检索方式与结果

`gh` 不在 PATH 中，未安装。以下检索均通过 GitHub REST API 的 `curl` 执行。GitHub 查询语言会把关键词当作 AND 条件，因此结果用于发现候选，候选元数据再从仓库端点逐个核实。

### 策略与回测框架

检索命令：

```bash
curl -sS -H 'Accept: application/vnd.github+json' \
  'https://api.github.com/search/repositories?q=algorithmic+trading+stars:%3E1000&sort=stars&per_page=30' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f\"{i['full_name']} | star={i['stargazers_count']} | push={i['pushed_at']} | archived={i['archived']} | {i['html_url']}\") for i in d.get('items',[])]"
```

返回结果节选（原始 API 输出字段）：

```text
QuantConnect/Lean | star=22630 | push=2026-11-20T14:34:38Z | archived=False
quantopian/zipline | star=20257 | push=2024-02-13T08:02:51Z | archived=False
StockSharp/StockSharp | star=11136 | push=2026-11-19T17:10:26Z | archived=False
ricequant/rqalpha | star=6889 | push=2026-10-28T02:43:18Z | archived=False
Superalgos/Superalgos | star=5811 | push=2026-11-14T19:54:14Z | archived=False
gbeced/pyalgotrade | star=4679 | push=2026-11-13T21:57:56Z | archived=True
edtechre/pybroker | star=3724 | push=2026-11-16T17:27:17Z | archived=False
coding-kitties/investing-algorithm-framework | star=2251 | push=2026-11-17T13:26:17Z | archived=False
```

另对已知框架清单执行仓库元数据查询，命令如下。API 返回的当前仓库字段列在下方比较表中。

```bash
for repo in freqtrade/freqtrade mementum/backtrader polakowo/vectorbt jesse-ai/jesse vnpy/vnpy; do
  curl -sS -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$repo"
done
```

本次 P1 提示词中更窄的搜索式 `q=trading+bot+technical+indicator+stars:%3E2000+language:python+pushed:%3E2025-01-01` 实际返回 `total_count=0`。这说明不能把某条查询式视为完整候选名录，故结合已有 `docs/github-candidates.json` 快照及仓库元数据端点继续核查。该快照也包含 freqtrade、jesse、hummingbot、investing-algorithm-framework 等原始检索结果。

### 图表界面库

检索命令：

```bash
curl -sS -H 'Accept: application/vnd.github+json' \
  'https://api.github.com/search/repositories?q=javascript+financial+chart+stars:%3E1000&sort=stars&per_page=15' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f\"{i['full_name']} | star={i['stargazers_count']} | push={i['pushed_at']} | archived={i['archived']} | {i['html_url']}\") for i in d.get('items',[])]"
```

返回结果：

```text
tradingview/lightweight-charts | star=17915 | push=2026-11-18T14:48:17Z | archived=False | https://github.com/tradingview/lightweight-charts
shashankvemuri/Finance | star=4393 | push=2026-09-12T01:00:07Z | archived=False | https://github.com/shashankvemuri/Finance
```

### 指标计算库

检索命令：

```bash
curl -sS -H 'Accept: application/vnd.github+json' \
  'https://api.github.com/search/repositories?q=technical+indicator+library+language:python+stars:%3E100&sort=stars&per_page=15' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f\"{i['full_name']} | star={i['stargazers_count']} | push={i['pushed_at']} | archived={i['archived']} | {i['html_url']}\") for i in d.get('items',[])]"
```

返回结果：

```text
kylejusticemagnuson/pyti | star=667 | push=2026-06-26T17:59:33Z | archived=False
jrmeier/fast-trade | star=607 | push=2026-10-16T04:05:35Z | archived=False
TulipCharts/tulipy | star=377 | push=2021-07-15T16:00:39Z | archived=False
vsaveris/trading-technical-indicators | star=153 | push=2025-11-23T17:26:18Z | archived=False
mr-easy/streaming_indicators | star=153 | push=2026-10-16T17:03:21Z | archived=False
alihaskar/pycharting | star=120 | push=2026-10-27T05:15:20Z | archived=False
```

`TA-Lib/ta-lib-python` 另通过仓库元数据端点核实，作为成熟的补充计算库纳入评估。P2 的规格要求指标实现保持 pandas/numpy 且从 YAML 参数读取，因此它不是本原型必须引入的依赖。

## 候选仓库数据

元数据字段由 `GET /repos/{owner}/{repo}` 查询。活跃度列为过去 90 天内被更新的 issues 与 PR 数，分别通过 GitHub issues 搜索端点统计（起始日 `2026-08-20`）。Stars、push 时间会随时间变化，以下为 2026-11-20 查询快照。

| 候选 | Stars | 最近 push (UTC) | License | 主语言 | Archived | 近 90 天 issue / PR 更新 | A-E 初审 |
|---|---:|---|---|---|---|---:|---|
| [jesse-ai/jesse](https://github.com/jesse-ai/jesse) | 8,823 | 2026-11-17 | MIT | Python | 否 | 17 / 33 | 通过 |
| [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | 57,098 | 2026-11-19 | GPL-3.0 | Python | 否 | 72 / 242 | 通过，需接受 GPL 传染性 |
| [vnpy/vnpy](https://github.com/vnpy/vnpy) | 46,437 | 2026-11-11 | MIT | Python | 否 | 19 / 44 | A 未找到同一信号三周期源码证据 |
| [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | 9,899 | 2026-11-11 | NOASSERTION | Python | 否 | 15 / 57 | D 未能从 API 确认允许二次开发的许可证 |
| [mementum/backtrader](https://github.com/mementum/backtrader) | 23,764 | 2024-08-19 | GPL-3.0 | Python | 否 | 0 / 3 | D 不通过，最近 push 超过 12 个月 |

近 90 天活跃度命令示例：

```bash
curl -sS -G -H 'Accept: application/vnd.github+json' \
  --data-urlencode 'q=repo:jesse-ai/jesse is:issue updated:>=2026-08-20' \
  'https://api.github.com/search/issues'
curl -sS -G -H 'Accept: application/vnd.github+json' \
  --data-urlencode 'q=repo:jesse-ai/jesse is:pr updated:>=2026-08-20' \
  'https://api.github.com/search/issues'
```

以上两条分别返回 `total_count=17` 和 `total_count=33`。其他仓库以相同查询条件取数。辅助仓库的 issues 与 PR 更新数：`freqtrade/frequi` 为 2 / 98，`tradingview/lightweight-charts` 为 6 / 94，`TA-Lib/ta-lib-python` 为 62 / 38。

### 许可证说明

- `MIT` 允许闭源或开源的衍生产品分发，需保留版权和许可证声明。
- `Apache-2.0` 允许二次开发及闭源分发，需履行许可证、NOTICE、修改声明等条件，并留意专利条款。
- `GPL-3.0` 允许修改和商用，但分发基于它的衍生作品时通常必须以 GPL-3.0 提供对应源码。路线 1 是 fork 框架，若产品计划闭源分发，Freqtrade 与 Backtrader 的 GPL 义务会与该计划冲突。此处是许可证筛查，不代替法律意见。
- `NOASSERTION` 表示 GitHub API 未能识别 SPDX 许可证，不能据此确认可二次开发，故 vectorbt 在 D 项不通过。
- `BSD-2-Clause`（TA-Lib Python wrapper）允许宽松再分发，保留版权与免责声明即可。

## 硬约束与源码证据

| 候选 | A 多周期 | B 自定义指标 | C K 线信号呈现 | D 许可证、活跃、未归档 | E 参数外置 | 判定 |
|---|---|---|---|---|---|---|
| Jesse | README 明确支持 simultaneous multiple timeframes；`jesse/strategies/Strategy.py` 的 `get_candles(exchange, symbol, timeframe)` 可按 timeframe 取 candle | 策略为 Python，指标可在独立模块自定义，策略可调用 `get_candles` | README 的交互图表展示 orders 和 completed trades；`jesse/mcp/resources/charts.md` 提供主图线、水平线和指标副图 API。策略订单可作为信号交易点呈现 | MIT；push 2026-11-17；archived=false | 策略读取本项目 `docs/indicators.yaml` 的 `params:`；框架策略有 `hyperparameters()` 扩展点 | 通过 |
| Freqtrade | `freqtrade/strategy/informative_decorator.py` 与官方 `@informative` / `merge_informative_pair` 多周期接口 | `populate_indicators()` 可写任意 pandas 公式 | FreqUI 显示订单/交易和注释；不按 deprecated `plot-dataframe` 评分 | GPL-3.0；活跃且未归档 | `IntParameter`、`DecimalParameter` 等参数类 | 通过，分发衍生产品需接受 GPL |
| Backtrader | 多 data feed 可在一个策略中访问 | 自定义 Indicator | Plot/observer 支持可视化，但用户需自己整理信号图示 | GPL-3.0；push 超过 12 个月 | 策略类 `params` | 淘汰：不满足 D 的 12 个月提交要求 |
| vectorbt | 多频数据可由用户对齐输入，原生策略契合度低于 Jesse/Freqtrade | NumPy/pandas 向量化自定义计算 | plotting API 可绘制交易点 | API license=`NOASSERTION`，活跃但不能确认二次开发权 | 参数可传入函数 | 淘汰：不满足 D 的许可证可确认要求 |
| VNpy | README 和模块文档能确认 CTA、portfolio、chart/backtester 组件，但本次未在源码中找到周/日/小时共同生成单一信号的充分证据 | Python CTA/portfolio 策略可扩展 | Chart Wizard / backtester 提供图形化回测 | MIT；活跃且未归档 | 框架策略参数机制 | 淘汰：A 的证据门槛未通过 |

Jesse 上游证据链接：

- README 多周期、交互图表、交易订单展示：[README.md](https://github.com/jesse-ai/jesse/blob/master/README.md)
- `get_candles(exchange, symbol, timeframe)`、策略订单与图表方法：[jesse/strategies/Strategy.py](https://github.com/jesse-ai/jesse/blob/master/jesse/strategies/Strategy.py)
- 主图指标线、水平价位与副图 API：[jesse/mcp/resources/charts.md](https://github.com/jesse-ai/jesse/blob/master/jesse/mcp/resources/charts.md)
- chart hooks 的实际策略测试：[jesse/strategies/TestStrategyChartsReport/__init__.py](https://github.com/jesse-ai/jesse/blob/master/jesse/strategies/TestStrategyChartsReport/__init__.py)

Jesse 的 candle API 返回 NumPy 数组，而项目指标接口要求 pandas DataFrame。P2 应在策略适配层把框架 candle 数组转为标准 OHLCV DataFrame，再调用框架无关的指标包；不要让独立指标包导入 Jesse API。

Freqtrade 证据与弃用说明：

- [freqtrade/strategy/informative_decorator.py](https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/strategy/informative_decorator.py) 提供 informative timeframe helper。
- [docs/commands/lookahead-analysis.md](https://github.com/freqtrade/freqtrade/blob/develop/docs/commands/lookahead-analysis.md) 是内置未来函数分析命令。
- [docs/plotting.md](https://github.com/freqtrade/freqtrade/blob/develop/docs/plotting.md) 将 `plot-dataframe` / `plot-profit` 标为 deprecated，并指向 FreqUI。因此其可视化评分依据 FreqUI，不计废弃命令。

## 七维度评分

评分 1-5，权重合计 100%。加权总分公式为 `sum(维度分 × 权重) / 5`，满分 100。为满足七维度口径，“自定义指标公式”和“Python+pandas 契合度”合并计一项；许可证维度同时评估二次开发成本。硬约束不通过者即使总分不低，也不进入最终选择。

| 维度 | 权重 |
|---|---:|
| 多时间框架 | 20% |
| 自定义指标 / Python+pandas 契合度 | 10% |
| 信号在 K 线或交易图表呈现 | 15% |
| 回测能力 | 15% |
| 活跃度 | 10% |
| 许可证与二次开发成本 | 15% |
| 路线 1 最小改动成本 | 15% |

| 候选 | 多周期 | 指标 / pandas | 信号图 | 回测 | 活跃 | 许可证 / 成本 | 路线 1 | 加权总分 | 硬约束结果 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Jesse | 5 | 4 | 4 | 4 | 4 | 5 | 5 | **90** | 通过 |
| Freqtrade | 5 | 5 | 5 | 5 | 5 | 1 | 4 | **85** | 通过，GPL 风险需接受 |
| VNpy | 3 | 4 | 4 | 4 | 5 | 5 | 3 | **78** | A 未证实，淘汰 |
| vectorbt | 4 | 5 | 3 | 5 | 4 | 1 | 3 | **70** | D 许可证未确认，淘汰 |
| Backtrader | 5 | 5 | 4 | 4 | 1 | 1 | 2 | **65** | D 最近提交不达标，淘汰 |

评分是结合路线 1 的相对适配度判断，不是仓库质量排名。Freqtrade 的功能匹配最强，但 GPL-3.0 对分发自有 fork 的源码义务显著降低了本项目的许可证得分。

## 最终选择与理由

最终选择：**Jesse**。

Jesse 以 MIT 许可和活跃维护通过了可二次开发条件，策略可以在同一信号流程里访问不同 timeframe 的 candle，交互图表能够呈现 orders、completed trades 和自定义指标。这样可保留路线 1 的回测与图表底座，把 Elder 计算和信号规则留在 pandas/numpy 独立模块，再从 `docs/indicators.yaml` 读取可配置参数。相较 Freqtrade，Jesse 避免了 fork 后闭源分发的 GPL-3.0 传染性；代价是未确认有独立的 lookahead-analysis 命令，且其交易市场适配需在 P2 根据用户指定的数据源验证。

### 淘汰项

- **Freqtrade**：没有淘汰。它是可行的备选，A-E 均通过且自带 `lookahead-analysis`，但 GPL-3.0 会影响 fork 的衍生作品分发，因此综合选择 Jesse。
- **Backtrader**：D 不通过。GitHub 显示最近 push 为 2024-08-19，超出近 12 个月；同时为 GPL-3.0。
- **vectorbt**：D 不通过。GitHub API 返回 `NOASSERTION`，无法确认框架许可证允许该路线下的二次开发分发。
- **VNpy**：A 的源码证据不足。本次检查到 CTA、portfolio strategy 与 chart/backtester 组件，但没有确认一个信号如何同时使用周、日、小时数据。
- **Lightweight Charts**：不是策略/回测框架，不参与主底座排序；适合作为后续独立前端的图表补充，Apache-2.0，TypeScript，17,915 stars，push 2026-11-18，90 天 issue/PR 更新 6/94。
- **FreqUI**：Freqtrade 的可视化补充而非独立策略底座，GPL-3.0，Vue，1,127 stars，push 2026-11-18，90 天 issue/PR 更新 2/98。
- **TA-Lib Python**：指标补充库而非回测底座，BSD-2-Clause，Cython，12,426 stars，push 2026-11-11，90 天 issue/PR 更新 62/38。当前规格要求独立 pandas/numpy 实现，暂不列为必须依赖。

## 落地信息

- 完整 clone 命令：`git clone https://github.com/jesse-ai/jesse.git /Users/kaixin/WorkBuddy/2026-11-20-21-16-17/jesse`
- 本地底座目录：`/Users/kaixin/WorkBuddy/2026-11-20-21-16-17/jesse`
- 策略文件：`/Users/kaixin/WorkBuddy/2026-11-20-21-16-17/jesse/strategies/ElderTripleScreen/__init__.py`
- 参数配置：唯一来源仍为 `/Users/kaixin/WorkBuddy/2026-11-20-21-16-17/codex-elder-trading/docs/indicators.yaml` 的 `params:`。独立指标包加载该 YAML，策略层调用独立包；周线、日线、小时线的 candle routes 按 Jesse 项目配置加入同一交易符号。
- 数据适配：Jesse candle 数组在策略边界转换为 pandas OHLCV DataFrame，再传入独立指标函数。
- P2 底座：必须引用 `/Users/kaixin/WorkBuddy/2026-11-20-21-16-17/jesse`，并把产品侧独立指标与测试留在 `codex-elder-trading` 项目中。P2 不应另选框架或重写 Jesse 的数据、回测、风控层。
- 未来函数检查：Jesse README 宣称多周期支持不带 look-ahead bias，但在本次检查的 README、策略 API 与图表文档中未找到独立的 `lookahead-analysis` 审计工具。结论是**没有确认自带同类诊断命令**。Freqtrade 明确有 `freqtrade lookahead-analysis`，可作为工具能力对照；P2/P4 对 Jesse 策略须通过只使用已收盘 candles 的代码审查和前后数据扰动测试验证。

---

## 补充：目标市场确定为 A 股（WorkBuddy 追加，2026-11-20 23:00）

用户在 P1 完成后确认目标市场是 **A 股（沪深）**，不是加密货币。本报告选型时该变量未纳入，故补记其影响；**上方原始调研数据与结论保留不改**。

- Jesse 是加密货币框架，`get_candles` 对接加密交易所，A 股数据源需额外适配层（akshare / baostock / 本地 CSV）。
- Jesse 的撮合规则（7×24 连续交易、无涨跌停、无 T+1）与 A 股不符，**用它计算的回测绩效不可信**；本产品的指标计算与买卖点标注放在框架无关的独立模块中，不受影响。
- 因此 P2 计划阶段须给出二选一对比并由用户拍板：① 保留 Jesse + 自建 A 股数据适配层；② 切换到 A 股原生框架（rqalpha / vnpy / pybroker），需增量重跑 P1。
- 硬约束 F「A 股数据源适配」已加入 `prompts/P1.txt`，供任何后续重跑使用。
- A 股规则详见 `AGENTS.md`「目标市场：A 股」节与 `docs/indicators.yaml` 的 `market:` 配置。
