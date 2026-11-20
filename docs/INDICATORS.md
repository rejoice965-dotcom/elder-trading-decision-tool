# 指标规格 v1.0（P0 产出 · 机器可读版见 `indicators.yaml`）

> **本规格基于公开资料交叉核对重建，非原书直引；`source_page` 一律为 `null`。**
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
| `source_page` 非 null 的条目 | **0**（禁止伪造） |

来源编号见 `INDICATOR_SPEC.md` 的「来源编号」表（S1~S6）。引文均为来源页面原句摘录，仅用于定位。

---

## 一、系统规则（SYS）

### SYS-01 三重滤网 Triple Screen
- 公式/结构：`screen1(tf_high) -> screen2(tf_mid) -> screen3(tf_low)`，周期比例约 5:1（默认 周/日/小时）
- 参数：`tf_high=1w, tf_mid=1d, tf_low=1h, ratio=5`
- 输入：`open, high, low, close, volume`（三个周期）
- 层级：框架
- 规则：`direction = f(screen1)`；`setup = g(screen2, direction)`；`trigger = h(screen3, setup)`；三层全部为真才产生信号
- confidence: A | source: S1 | quote: "In his first book, 'Trading for a Living,' Elder defined his Triple Screen Trading System." | source_page: null | status: implement

### SYS-02 方向铁律
- 公式：`if direction == LONG: allowed_sides = {LONG}; elif direction == SHORT: allowed_sides = {SHORT}; else: allowed_sides = {}`
- 参数：无
- 输入：`direction`
- 层级：框架
- 规则：第 1 重定为多头时，整周只允许做多，日线级逆势卖出信号一律丢弃；EMA 走平不交易
- confidence: A | source: S1 | quote: "Screen one is strict filter: no exceptions." | source_page: null | status: implement

### SYS-03 第 1 重（周线定方向）
- 公式：`ema_slope = EMA(close,13) - EMA(close,13).shift(1)`；`hist_slope = macdhist - macdhist.shift(1)`（最近两根柱）；`direction = LONG if (ema_slope>0 and hist_slope>0) else SHORT if (ema_slope<0 and hist_slope<0) else FLAT`
- 参数：`ema_period=13, macd_fast=12, macd_slow=26, macd_signal=9`
- 输入：`close`（周线）
- 层级：第 1 重 / 趋势
- 规则：两者共振确认趋势；冲突视为中性、不交易
- confidence: A | source: S1, S2 | quote: "Elder showed that a trader could use the slope of the two most recent bars on a MACD histogram to determine the trend." | source_page: null | status: implement

### SYS-04 第 2 重（日线找逆势回调）
- 公式：`setup = oscillator_oversold_or_bullish_divergence(mid)` when `direction==LONG`；`setup = oscillator_overbought_or_bearish_divergence(mid)` when `direction==SHORT`
- 参数：`fi_ema=2, rsi_period=14, stoch_k=13, stoch_d=3, oversold=30, overbought=70`
- 输入：`close, high, low, volume`（日线）
- 层级：第 2 重 / 振荡
- 规则：升势买超卖（buy weakness），跌势卖超买（sell strength）；逆势信号一律忽略
- confidence: A | source: S1 | quote: "oscillator divergences are used to buy short-term weakness in uptrends, or to sell short-term strength in downtrends" | source_page: null | status: implement

### SYS-05 第 3 重（盘中挂单择时）
- 公式：`buy_stop = high.shift(1) + tick`；`sell_stop = low.shift(1) - tick`
- 参数：`breakout_offset=1 tick`
- 输入：`high, low, close`（小时线）
- 层级：第 3 重
- 规则：周线多头 + 日线回调到位 → 昨日最高价上方挂 buy stop；周线空头 → 昨日最低价下方挂 sell stop。突破才成交
- confidence: A | source: S1 | quote: "a buy stop order to catch an upside breakout by buying at the previous day's high" | source_page: null | status: implement

> 差异记录：S4（中文二手）主张第 3 重是「包络线触轨 + K 线反转形态」，与 S1 冲突。采用 S1 版本，S4 版本列入不实现清单。

---

## 二、指标（IND）

| id | 名称 | 公式 | 参数（默认/备选） | 输入 | 买卖规则 | conf | 来源 / 引文 | status |
|---|---|---|---|---|---|---|---|---|
| IND-01 | EMA 指数移动平均 | `EMA(close, n)` | 13 / 26 | close | 斜率>0 多头，<0 空头，≈0 观望 | A | S1,S2 "Elder's preferred trend-following tool" | implement |
| IND-02 | MACD 线 + 柱状图 | `macd=EMA(f)-EMA(s)`; `signal=EMA(macd,g)`; `hist=macd-signal` | 12,26,9 / 11,25,8 | close | `hist` 斜率转折或柱与价格背离 → 力量转折 | A | S2 "The slope of the histogram — not its absolute level — is the primary signal." | implement |
| IND-03 | Force Index 强力指数 | `fi=(close-close.shift(1))*volume`; `out=EMA(fi, m)` | m=2 / 13, 1(原始) | close, volume | `out<0` 且价格底背离 → 买；`out>0` 且顶背离 → 卖 | A | S1 "Force Index is calculated by subtracting yesterday's close from today's close and multiplying that by today's volume." | implement |
| IND-04 | Elder-Ray | `bull=high-EMA(close,13)`; `bear=low-EMA(close,13)` | ema=13 | high, low, close | 买：`close>ema13 & bear<0 & bear> bear.shift(1)`（最好底背离）且 `bull` 创新高；卖镜像 | A | S1 "Elder Ray consists of two measures - Bull Power and Bear Power." | implement |
| IND-05 | Stochastic K/D | `K=100*(close-LLV(n))/(HHV(n)-LLV(n))`; `D=SMA(K,d)` | k=13 / 14, d=3, 阈值 30/70 | high, low, close | 升势：K 跌破 30 后上穿 30 → 买；跌势镜像 | A | S1 "Elder suggests Force Index (2-day EMA), Elder-Ray (bull/bear power), or 13-day Stochastic." | implement |
| IND-06 | RSI 相对强弱 | Wilder RSI(`close`, n) | 14 / **7（二手资料称 7，无原书可证）** | close | 背离 + 超买超卖；禁止单独逆势抄底摸顶 | A（公式）/ B（周期） | S2, S5 | implement |
| IND-07 | Williams %R | `WR=-100*(HHV(n)-close)/(HHV(n)-LLV(n))` | 待核对 | high, low, close | 超买超卖 + 背离 | B | S5；无可核验短引 → `unverified` | optional |
| IND-08 | 背离分类 A/B/C | A：价格创新高/低而指标未创新高/低；B：双顶/底+指标走弱；C：指标持平 | 无 | price + 任一振荡指标 | A 类最强反转信号 | B | S5 "Class A: when price reaches a new high/low, an oscillator reaches a lower high/higher bottom" | optional |
| IND-09 | 成交量 Volume | 原始 `volume` 柱 | 无 | volume | 放量上涨/缩量回调为健康；价格新高而量萎缩为乏力 | A | S1, S4 | implement |
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
| `rsi_period` | 14 | 7 | S4（二手） | 无原书可证，界面可切 7 |
| `stoch_k/stoch_d` | 13 / 3 | 14 / 5 | S1 | 阈值 30/70 |
| `tf_high/tf_mid/tf_low` | 1w / 1d / 1h | 1M / 1w / 1d | S1,S2 | 约 5:1 递进 |
| `risk_per_trade` | 0.02 | 0.01 | S2 | 单笔最大风险 |
| `monthly_drawdown_limit` | 0.06 | — | S2 | 月度熔断 |

**禁止**把上表任何数字硬编码进策略；`docs/indicators.yaml` 的 `params:` 是唯一入口。

---

## 五、不实现清单

| 项目 | 理由 |
|---|---|
| Impulse System（K 线染绿/红/蓝） | S1 明确属《Come into my Trading Room》(2002)，非 1993 年本书 |
| SafeZone、Chandelier、Market Thermometer、AutoEnvelope | S3 显示出自覆盖两本书的 MetaStock 插件；S4 混入本书清单 |
| ATR(13) 止损基准、Envelope(20,±2.5%)、布林带、Keltner 作为第 3 重主力 | 与 S1 复述的原版第 3 重（前日高低点突破挂单）冲突，且无原书可判定 |
| 通道触轨 + K 线反转形态作为第 3 重 | 同上，采用 SYS-05 |
| 任何 ML / LLM 预测 | 与本书方法论无关 |

## 六、待确认 / 需用户决策

1. RSI 周期取 14 还是 7（无原书可证）→ 默认 14，配置可切。
2. `optional` 四项（IND-07/08/10/12）是否实现 → 默认跳过。
3. 目标市场与数据源（股票/加密/期货）、回测区间 → 由用户指定。
4. 将来拿到书 → 跑 `prompts/P0-R.txt` 回填页码与原文，全部升级为 `book-confirmed`。
