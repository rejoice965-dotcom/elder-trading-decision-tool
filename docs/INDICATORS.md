# 指标规格 v1.0（P0 产出 · 机器可读版见 `indicators.yaml`）

> **本规格以公开资料交叉核对为基础。15 条已按用户确认的原书第2版资料回填真实页码，6 条仍为 `null`；未确认内容不得编造。**
> 用户没有《以交易为生》电子版。全仓库禁止编造章节号、页码或"书中原文"。
> 事实源：`INDICATOR_SPEC.md`（v1.0）。代码只读 `docs/indicators.yaml` 的 `params:`。
> 本文件由 WorkBuddy 代跑 P0 生成（本机 Codex CLI 在受限执行环境中无法写文件，详见 `CODEX_PROMPTS.md` 第 1.1 节）。

## 汇总

| 项 | 数量 |
|---|---|
| 条目总数 | 21 |
| confidence A（多来源交叉确认） | 15 → `status: implement` |
| confidence B（二手整理） | 4 → `status: optional`（默认不实现） |
| confidence C（后续著作/插件） | 2 → `status: skip` |
| 已回填书内依据 | **15**（原书第2版） |
| 仍为 `source_page: null` 的条目 | **6**（待补） |

来源编号见 `INDICATOR_SPEC.md` 的「来源编号」表（S1~S6）。引文均为来源页面原句摘录，仅用于定位。

---

## 一、系统规则（SYS）

### SYS-01 三重滤网 Triple Screen
- 公式/结构：`screen1(tf_high) -> screen2(tf_mid) -> screen3(tf_low)`，周期比例约 5:1（默认 周/日/小时）
- 参数：`tf_high=1w, tf_mid=1d, tf_low=1h, ratio=5`
- 输入：`open, high, low, close, volume`（三个周期）
- 层级：框架
- 规则：`direction = f(screen1)`；`setup = g(screen2, direction)`；`trigger = h(screen3, setup)`；三层全部为真才产生信号
- confidence: A | source: S1 | quote: "In his first book, 'Trading for a Living,' Elder defined his Triple Screen Trading System." | source_page: p.224 | status: implement

### SYS-02 方向铁律
- 公式：`if direction == LONG: allowed_sides = {LONG}; elif direction == SHORT: allowed_sides = {SHORT}; else: allowed_sides = {}`
- 参数：无
- 输入：`direction`
- 层级：框架
- 规则：第 1 重定为多头时，整周只允许做多，日线级逆势卖出信号一律丢弃；EMA 走平不交易
- confidence: A | source: S1 | quote: "Screen one is strict filter: no exceptions." | source_page: p.229, p.113 | status: implement

### SYS-03 第 1 重（周线定方向）
- 公式：`ema_slope = EMA(close,13) - EMA(close,13).shift(1)`；`hist_slope = macdhist - macdhist.shift(1)`（最近两根柱）；`direction = LONG if (ema_slope>0 and hist_slope>0) else SHORT if (ema_slope<0 and hist_slope<0) else FLAT`
- 参数：`ema_period=13, macd_fast=12, macd_slow=26, macd_signal=9`
- 输入：`close`（周线）
- 层级：第 1 重 / 趋势
- 规则：两者共振确认趋势；冲突视为中性、不交易
- confidence: A | source: S1, S2 | quote: "Elder showed that a trader could use the slope of the two most recent bars on a MACD histogram to determine the trend." | source_page: p.228 | status: implement

### SYS-04 第 2 重（日线找逆势回调）
- 公式：使用信号日前最近已收盘交易日的 qfq 日线。周线方向为 LONG 时，`(Bear Power < 0 且较前一根日线上升) 或 K <= oversold 或 RSI <= oversold`。方向为 SHORT 时，`(Bull Power > 0 且较前一根日线下降) 或 K >= overbought 或 RSI >= overbought`。
- 参数：`ema_period`、`rsi_period`、`stoch_k`、`oversold`、`overbought`。
- 输入：`close, high, low`（前复权日线）。
- 层级：第 2 重 / 振荡。
- 规则：同方向三者任一成立即 setup。方向为 FLAT 时无 setup。项目采用 S1 允许任选振荡器的思路，使用已确认的简化条件。
- confidence: A | source: S1 | quote: "oscillator divergences are used to buy short-term weakness in uptrends, or to sell short-term strength in downtrends" | source_page: p.229, p.230, p.143 | status: implement

### SYS-05 第 3 重（盘中挂单择时）
- 公式：`buy_stop = high_raw[T-1] + offset`，`sell_stop = low_raw[T-1] - offset`，其中 `offset = breakout_offset_ticks × price_tick`。T-1 是信号日前一交易日，原始高低点字段直接记录该日 raw 价格。
- 参数：`breakout_offset_ticks`、`market.price_tick`
- 输入：`high, low, close`（小时线）
- 层级：第 3 重
- 规则：周线多头 + 日线回调到位 → 前一交易日 raw 最高价上方设置 buy stop。周线空头 + 日线反弹到位 → 前一交易日 raw 最低价下方设置 sell stop。已收盘 60 分钟 K 达到阈值时产生候选信号。BUY 的保护止损参考 T-1 raw 低点，SELL 参考 T-1 raw 高点
- confidence: A | source: S1 | quote: "a buy stop order to catch an upside breakout by buying at the previous day's high" | source_page: p.231, p.236, p.232 | status: implement

> 差异记录：S4（中文二手）主张第 3 重是「包络线触轨 + K 线反转形态」，与 S1 冲突。采用 S1 版本，S4 版本列入不实现清单。

---

## 二、指标（IND）

| id | 名称 | 公式 | 参数（默认/备选） | 输入 | 买卖规则 | conf | 来源 / 引文 | status |
|---|---|---|---|---|---|---|---|---|
| IND-01 | EMA 指数移动平均 | `EMA(close, n)` | 13 / 26 | close | 斜率>0 多头，<0 空头，≈0 观望 | A | S1,S2 "Elder's preferred trend-following tool" | implement |
| IND-02 | MACD 线 + 柱状图 | `macd=EMA(f)-EMA(s)`; `signal=EMA(macd,g)`; `hist=macd-signal` | 12,26,9 / 11,25,8 | close | `hist` 斜率转折或柱与价格背离 → 力量转折 | A | S2 "The slope of the histogram — not its absolute level — is the primary signal." | implement |
| IND-03 | Force Index 强力指数 | `fi=(close-close.shift(1))*volume`; `out=EMA(fi, m)` | m=2 / 13, 1(原始) | close, volume | 计算后随信号输出，Force Index 背离为 optional | A | S1 "Force Index is calculated by subtracting yesterday's close from today's close and multiplying that by today's volume." | implement |
| IND-04 | Elder-Ray | `bull=high-EMA(close,13)`; `bear=low-EMA(close,13)` | ema=13 | high, low, close | LONG：Bear Power 为负且回升。SHORT：Bull Power 为正且回落 | A | S1 "Elder Ray consists of two measures - Bull Power and Bear Power." | implement |
| IND-05 | Stochastic K/D | `K=100*(close-LLV(n))/(HHV(n)-LLV(n))`; `D=SMA(K,d)` | k=13 / 14, d=3, 阈值 30/70 | high, low, close | LONG：K ≤ oversold。SHORT：K ≥ overbought。穿回阈值为 optional | A | S1 "Elder suggests Force Index (2-day EMA), Elder-Ray (bull/bear power), or 13-day Stochastic." | implement |
| IND-06 | RSI 相对强弱 | Wilder RSI(`close`, n) | 14（第2版建议7～9日、另有13日示例；按用户决定保持14） | close | LONG：RSI ≤ oversold。SHORT：RSI ≥ overbought | A（公开资料公式） | S2, S5 | implement |
| IND-07 | Williams %R | `WR=-100*(HHV(n)-close)/(HHV(n)-LLV(n))` | 待核对 | high, low, close | 超买超卖 + 背离 | B | S5；无可核验短引 → `unverified` | optional |
| IND-08 | 背离分类 A/B/C | A：价格创新高/低而指标未创新高/低；B：双顶/底+指标走弱；C：指标持平 | 无 | price + 任一振荡指标 | A 类最强反转信号 | B | S5 "Class A: when price reaches a new high/low, an oscillator reaches a lower high/higher bottom" | optional |
| IND-09 | 成交量 Volume | 原始 `volume` 柱 | 无 | volume | 原始成交量透传，量价确认为 optional | A | S1, S4 | implement |
| IND-10 | OBV 能量潮 | `OBV_t = OBV_{t-1} ± volume_t` | 无 | close, volume | 价格新高 OBV 未新高 → 动能减弱 | B | S4, S5；`unverified` | optional |
| IND-11 | A/D、Herrick Payoff Index | 待核对 | — | — | 验证量价力量 | C | S5 | skip |
| IND-12 | 趋势线、支撑/阻力 | 画线 | — | high, low, close | 触碰越多越有效；假突破用背离识别 | B | S5；`unverified` | optional |
| IND-13 | 缺口、K 线反转形态、头肩/双顶双底 | 形态识别 | — | OHLC | 共振确认，不单独开仓 | C | S4 | skip |

---

## 三、资金管理（RISK）

| id | 名称 | 公式 | conf | 来源 / 引文 | status |
|---|---|---|---|---|---|
| RISK-01 | 2% 法则 | `max_risk = equity*0.02`; `size = max_risk/(entry-stop)`；**先定止损距离再算仓位** | A | S2 "Never risk more than 2% of total trading capital on a single trade." | implement |
| RISK-02 | 6% 法则 | `if (month_open_equity-equity) > 0.06*month_open_equity: halt_trading(rest_of_month)` | A | S2 "If the account falls 6% below its monthly opening balance, stop trading for the rest of that month." | implement |
| RISK-03 | 50% 法则 | `stop = entry + 0.5*(best_price-entry)`（多单）| A | S2 "the stop is moved to a level that protects at least half the paper gain" | implement |

---

## 四、参数待定表（全部必须做成配置项）

| 参数 | 默认值 | 备选值 | 依据 | 说明 |
|---|---|---|---|---|
| `ema_period` | 13 | 26 | S1 | 13 日 EMA；周线用 13 周 |
| `macd_fast/slow/signal` | 12 / 26 / 9 | 11 / 25 / 8 | S1,S2 | S1 提到 Elder 后续演示用 11,25,8 |
| `fi_ema` | 2 | 13, 1 | S1,S2 | 短线 2 日 EMA，中线 13 日 EMA |
| `rsi_period` | 14（第2版建议 7～9 日，另有 13 日示例；按用户决定保持 14） | 7 | 第2版 p.145 | 配置项 `rsi_period`，保持 14 |
| `stoch_k/stoch_d` | 13 / 3 | 14 / 5 | S1 | 阈值 30/70 |
| `tf_high/tf_mid/tf_low` | 1w / 1d / 1h | 1M / 1w / 1d | S1,S2 | 约 5:1 递进 |
| `risk_per_trade` | 0.02 | 0.01 | S2 | 单笔最大风险 |
| `monthly_drawdown_limit` | 0.06 | — | S2 | 月度熔断 |

**禁止**把上表任何数字硬编码进策略；`docs/indicators.yaml` 的 `params:` 是唯一入口。

---

## 五、不实现清单

### Optional 未实现规则

| 条目 | 规则 | 状态 |
|---|---|---|
| IND-03 | Force Index 背离 | optional |
| IND-05 | Stochastic 穿回阈值 | optional |
| IND-09 | 量价确认 | optional |

### 排除项

| 项目 | 理由 |
|---|---|
| Impulse System（K 线染绿/红/蓝） | 第2版正文 p.236-242 存在；按用户决定本期仍不实现，列为二期 optional 候选 |
| SafeZone、Chandelier、Market Thermometer、AutoEnvelope | S3 显示出自覆盖两本书的 MetaStock 插件；S4 混入本书清单 |
| ATR(13) 止损基准、Envelope(20,±2.5%)、布林带、Keltner 作为第 3 重主力 | 与 S1 复述的原版第 3 重（前日高低点突破挂单）冲突，且无原书可判定 |
| 第41节通道交易系统 | 第2版正文 p.242 起存在；按用户决定本期仍不实现，列为二期 optional 候选 |
| 通道触轨 + K 线反转形态作为第 3 重 | S4 版本，采用 SYS-05 |
| 任何 ML / LLM 预测 | 与本书方法论无关 |

### 第2版差异（按用户决定保持现状）

- **D4 / IND-06**：第2版建议 RSI 7～9 日，另有 13 日示例；项目保留 `rsi_period=14`。
- **D6 / IND-05**：第2版标准随机指标 %K 时间跨度为 5 日；项目保留 `stoch_k=13`。
- **D7 / SYS-04**：第2版 p.167 记载「2日EMA可以很好地与三重滤网交易系统（见第39节）相适应。」p.229 说明将振荡指标用于日线。按决定保留三选一 setup，Force Index 触发列为 optional。
- **D8 / RISK-02**：第2版 p.304 将当月损失与持仓头寸风险额度之和计入 6% 限额。项目按用户决定维持当前实现，不改风控代码。
- **D1**：Impulse System 正文见第2版 p.236-242，仍不实现并列二期 optional；第41节通道交易系统从 p.242 起，处理相同。

## 六、已决事项与待补依据

1. RSI 周期按用户决定保持 14。第2版 7～9 日建议与 13 日示例作为差异记录。
2. `optional` 指标和附加规则按用户决定默认跳过。
3. 目标市场与数据源已按项目决定为 A 股和 AkShare。
4. 第2版依据已回填 15 条；IND-04、IND-07、IND-10、IND-12、IND-13、RISK-03 共 6 条待补书页，保持 `source_page: null`。
## 七、书内确认（第2版）

版本：《以交易为生》（原书第2版），[美]亚历山大·埃尔德（Alexander Elder）著，熊振华译，机械工业出版社 2017.6 第1版（2020.6 第8次印刷），ISBN 978-7-111-56972-5。章节、页码和短引逐字取自用户确认的 `docs/book_references.csv`，书页照片编号见 CSV notes。

| spec_id | 章节 | 页码 | 短引 |
|---|---|---|---|
| SYS-01 | 第7章 交易系统 · 第39节 三重滤网交易系统 | p.224 | 它最基本的原理一直保持不变：使用多重时间周期和技术指标进行交易决策。 |
| SYS-02 | 第7章 交易系统 · 第39节 第一重滤网总结 | p.229 | 在上升的趋势里只允许你选择买入或者观望；在下跌的趋势里只允许你卖出或观望。 |
| SYS-02 | 第4章 计算机化的技术分析 · 第22节 移动平均 · 交易规则 | p.113 | 当EMA走平，只是小幅波动时，那意味着一种漫无目的、没有趋势的市场。这种情况下不要使用趋势跟随方法。 |
| SYS-03 | 第7章 交易系统 · 第39节 第一重滤网——市场潮流 | p.228 | MACD的斜率由最近两根MACD柱线之间的关系确定。 |
| SYS-04 | 第7章 交易系统 · 第39节 第二重滤网——市场浪涛 | p.229 | 将震荡指标应用于日线图之中。 |
| SYS-04 | 第7章 交易系统 · 第39节 第二重滤网——市场浪涛 | p.230 | 当周趋势是上升的，三重滤网仅允许采用日线图震荡指标发出的买入信号，而不会允许采用其发出的卖出信号。 |
| SYS-04 | 第4章 计算机化的技术分析 · 第26节 随机指标 · 「交易规则」 | p.143 | 三重滤网交易系统只有当周趋势向上时，随机指标给出的买入信号才会被采用。 |
| SYS-05 | 第7章 交易系统 · 第39节 第三重滤网——买入技术 | p.231 | 做多时，在日线向上突破前一交易日高点的时候买入；卖空时，在日线向下突破前一交易日低点的时候卖出。 |
| SYS-05 | 第7章 交易系统 · 第39节 第三重滤网——买入技术 | p.236 | 三重滤网交易系统需要设置相对保守的止损价位。 |
| SYS-05 | 第7章 交易系统 · 第39节 第三重滤网——买入技术 | p.232 | 突破技术仍然是有效的，但是我很少使用它了。 |
| IND-01 | 第4章 计算机化的技术分析 · 第22节 移动平均 · 「选择移动平均的长度」 | p.111 | 监控EMA的斜率是很有益的，因为上升的斜率意味着上涨趋势，而下降的斜率意味着下跌趋势。 |
| IND-01 | 第4章 计算机化的技术分析 · 第22节 移动平均 · 「选择移动平均的长度」 | p.115 | 使用26周和13周的EMA来分析周线图，或者22日和11日的EMA来分析日线图。 |
| IND-01 | 第4章 计算机化的技术分析 · 第22节 移动平均 · 「选择移动平均的长度」 | p.110 | 指数移动平均（以下简称EMA）是一种更好的趋势跟随指标 |
| IND-02 | 第4章 计算机化的技术分析 · 第23节 MACD 线和 MACD 柱状线 · 背离 | p.127 | 当MACD柱状线从第二个底部开始反转时，它就发出了买入的信号。 |
| IND-02 | 第4章 计算机化的技术分析 · 第23节 MACD 线和 MACD 柱状线 · 背离 | p.129 | 当MACD柱状线从第二个顶点开始下降时，就已经是卖出的信号了。 |
| IND-02 | 第4章 计算机化的技术分析 · 第23节 MACD 线和 MACD 柱状线 · 背离 | p.128 | 26日和13日指数移动平均线，12-26-9MACD线和柱状图 |
| IND-03 | 第5章 成交量和时间 · 第30节 强力指数指标 · 「如何构造强力指数指标」 | p.163 | 强力指数指标＝今日成交量×（今日收盘价－昨日收盘价） |
| IND-03 | 第5章 成交量和时间 · 第30节 强力指数指标 · 「如何构造强力指数指标」 | p.167 | 2日EMA可以很好地与三重滤网交易系统（见第39节）相适应。 |
| IND-03 | 第5章 成交量和时间 · 第30节 强力指数指标 · 「如何构造强力指数指标」 | p.163 | 当13日EMA穿越到中心线上方时，表明多头占据优势，此时是买入时机 |
| IND-05 | 第4章 计算机化的技术分析 · 第26节 随机指标 | p.139 | 随机指标的标准时间跨度是5天，虽然有些交易者会用更多的天数。 |
| IND-05 | 第4章 计算机化的技术分析 · 第26节 随机指标 | p.141 | 随机指标的取值范围是0～100。通常在20%和80%的地方画参考线，标识出超买和超卖的区域。 |
| IND-06 | 第4章 计算机化的技术分析 · 第27节 相对强弱指标 | p.144 | 相对强弱指标（RSI）是由威尔斯·威尔德发明的一个震荡指标。 |
| IND-06 | 第4章 计算机化的技术分析 · 第27节 相对强弱指标 | p.145 | 交易信号在短期内的RSI上看得更清楚，比如7～9天的RSI。 |
| IND-06 | 第4章 计算机化的技术分析 · 第27节 相对强弱指标 | p.146 | 这些线通常是在30%和70%的地方。 |
| IND-08 | 第4章 计算机化的技术分析 · 第23节 MACD 线和 MACD 柱状线 · 背离 | p.127 | 熊市背离显示出多方的能量在耗尽，价格还在惯性上涨，但空方已经准备入场接手。 |
| IND-08 | 第4章 计算机化的技术分析 · 第23节 MACD 线和 MACD 柱状线 · 背离 | p.129 | 三重牛市或熊市背离由三组价格和震荡指标的底部或者三组价格和震荡指标的顶部组成。 |
| IND-09 | 第5章 成交量和时间 · 第30节 强力指数指标 · 「交易心理学」 | p.164 | 成交量反映了市场参与者的情绪卷入程度。 |
| IND-11 | 第5章 成交量和时间 · 第29节 以成交量为基础的指标 · 「更多关于 A/D 值」 | p.162 | 在A/D和日本蜡烛图之间有很强的类似性，它们都关注开盘价和收盘价之间的差异。 |
| RISK-01 | 第9章 风险管理 · 第50节 2%法则 | p.296 | 2%原则会防止你的账户在单次交易中出现本金亏损2%以上的风险。 |
| RISK-01 | 第9章 风险管理 · 第50节 2%法则 | p.298 | 将A除以B，得到所能交易的最大股数。 |
| RISK-02 | 第9章 风险管理 · 第51节 6%法则 | p.302 | 6%原则能给每一个账户都设了一个当月最大回撤比例。 |
| RISK-02 | 第9章 风险管理 · 第51节 6%法则 | p.304 | 如果两者之和已经超过你月初账户资产的6%时，这个月剩下的时间你都不能再增加交易头寸了 |
