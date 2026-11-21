# 《以交易为生》指标规格 v1.0 — Mode B 事实源

> **这是什么**：用户没有《以交易为生》电子版。本表是从**公开资料交叉核对重建**的指标规格，作为项目唯一事实源（由 P0 规范化为 `docs/INDICATORS.md` + `docs/indicators.yaml`）。
> **诚实声明（必须随规格一路带到代码和界面）**：本规格**不是原书直引**。所有 `source_page` 为 `null`；禁止编造章节号、页码或"书中原文"。
> **溯源格式**：`source_url + source_quote(≤50字) + confidence`。界面与信号面板上必须显示「依据：公开资料交叉核对，非原书直引」。

## 来源编号

| 编号 | 来源 | 用途 |
|---|---|---|
| S1 | CMT Association《Technically Speaking》2004/05，复述 Elder 在 *Trading for a Living* 定义的 Triple Screen / Elder-Ray / Force Index — https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf | 权威交叉确认；明确 Impulse System 属 2002 年后续著作 |
| S2 | *Trading for a Living* 术语与方法汇总 — https://www.marketsfn.com/book/trading-for-a-living | 2%/6%/50% 法则、Elder-Ray、Force Index、MACD-Histogram 定义 |
| S3 | Elder 官方 MetaStock 插件指标清单 — https://forestbergen.com/portfolio-item/join-dr-alexander-elder-in-his-trading-room | 判定哪些指标属后续著作/插件体系 |
| S4 | 中文二手指标梳理（微信公众号《以交易为生》全书指标梳理） | 参数细节来源，**B 级，需标注为二手** |
| S5 | 读书笔记 — https://aloycwl.blogspot.com/2022/03/trading-for-living-alexander-elder-1993.html | 背离分类、指标分组 |
| S6 | Freqtrade 官方文档 — https://www.freqtrade.io/en/stable/plotting/ | 选型事实：`plot-dataframe` 已 deprecated |

**置信度 / 实现状态**：
- `A` = 多个独立来源交叉确认属本书 → `status: implement`
- `B` = 二手整理、参数有分歧 → `status: optional`（默认不实现，除非我批准）
- `C` = 疑似出自后续著作或插件 → `status: skip`

---

## 一、总装配框架（必须先实现）

| id | 名称 | conf | 内容 | 来源 | status |
|---|---|---|---|---|---|
| SYS-01 | 三重滤网 Triple Screen | A | 三个时间框架约 5:1 递进。第 1 重（周线/潮汐 Tide）定方向；第 2 重（日线/波浪 Wave）用振荡指标找逆大势回调；第 3 重（盘中/涟漪 Ripple）用挂单择时 | S1, S2 | implement |
| SYS-02 | 方向铁律 | A | 第 1 重多头时整周只做多，日线级逆势卖出信号一律忽略；反之亦然。EMA 走平不交易 | S1 | implement |
| SYS-03 | 第 1 重实现 | A | 13 周 EMA 斜率 + 周线 MACD 柱状图**最近两根柱的斜率**（不是金叉死叉）。两者共振确认趋势，冲突视为中性、不交易 | S1, S2 | implement |
| SYS-04 | 第 2 重实现 | A | 读取 T-1 已收盘 qfq 日线。LONG：Bear Power 为负且较前一根日线上升、Stochastic K ≤ oversold、RSI ≤ oversold，任一成立即 setup。SHORT：Bull Power 为正且较前一根日线下降、Stochastic K ≥ overbought、RSI ≥ overbought，任一成立即 setup。FLAT 无 setup。简化条件基于 S1 任选振荡器的思路 | S1 | implement |
| SYS-05 | 第 3 重实现 | A | 周线多头且日线 setup 成立时，以信号日前一交易日（T-1）的 raw 高点加 `breakout_offset_ticks × price_tick` 为 buy stop。周线空头且日线 setup 成立时，以 T-1 raw 低点减同一偏移为 sell stop。已收盘 60 分钟 K 达到阈值时产生候选信号。原始高低点字段直接记录 T-1 raw 价格，BUY 保护止损参考该日低点，SELL 参考该日高点 | S1 | implement |

> ⚠️ S4 把第 3 重写成「包络线触轨 + K 线反转形态」，与 S1 复述的原版（突破前日高低点的追踪止损单）冲突。**采用 S1 版本（SYS-05）**，S4 版本记入「不实现清单」，差异写进规格文档。

## 二、指标逐条

| id | 指标 | conf | 公式 / 参数 | 买卖规则 | 层级 | 来源 | status |
|---|---|---|---|---|---|---|---|
| IND-01 | EMA 指数移动平均 | A | `EMA(close, 13)`；周线用 13 周 EMA | 斜率向上=多头，向下=空头，走平=观望 | 趋势/第1重 | S1, S2 | implement |
| IND-02 | MACD 线 + 柱状图 | A | `MACD(12,26,9)`；`hist = macd - signal`。Elder 强调**柱状图斜率**而非绝对值 | 柱由负转正向上、或柱与价格背离，为力量转折信号 | 趋势+摆动/第1、2重 | S1, S2 | implement |
| IND-03 | Force Index 强力指数 | A | `FI_raw = (close_t - close_{t-1}) * volume_t`；再取 `EMA(FI_raw, 2)` 短线 / `EMA(FI_raw, 13)` 中线 | 计算后随信号输出，Force Index 背离为 optional | 摆动/第2重（Elder 首选） | S1, S2 | implement |
| IND-04 | Elder-Ray 埃尔德射线 | A | `BullPower = high - EMA(close,13)`；`BearPower = low - EMA(close,13)`，直方图 | LONG：Bear Power 为负且回升。SHORT：Bull Power 为正且回落 | 摆动/第2重 | S1, S2 | implement |
| IND-05 | Stochastic K/D | A | 周期有分歧（S1 提 13 日）。超买超卖阈值 30/70 | LONG：K ≤ oversold。SHORT：K ≥ overbought。穿回阈值为 optional | 摆动/第2重 | S1 | implement |
| IND-06 | RSI 相对强弱 | A | **周期有分歧**：S4 写 7，市面常用 14 | LONG：RSI ≤ oversold。SHORT：RSI ≥ overbought | 摆动/第2重 | S2, S4, S5 | implement |
| IND-07 | Williams %R | B | 参数待核对 | 超买超卖 + 背离 | 摆动/第2重 | S5 | optional |
| IND-08 | 背离分类 A/B/C | B | A：价格创新高/低而指标未创新高/低（最强）；B：双顶/双底+指标走弱；C：指标持平 | A 类最强反转信号 | 摆动/全层级 | S2, S5 | optional |
| IND-09 | 成交量 Volume | A | 原始成交量柱 | 原始成交量透传，量价确认为 optional | 量能/验证 | S1, S4 | implement |
| IND-10 | OBV 能量潮 | B | 上涨日加量、下跌日减量累计 | 价格新高 OBV 未新高 → 动能减弱 | 量能/验证 | S4, S5 | optional |
| IND-11 | A/D、Herrick Payoff Index | C | 公式待核对 | 验证量价力量 | 量能/验证 | S5 | skip |
| IND-12 | 趋势线、支撑/阻力 | B | 画线 | 触碰越多越有效；假突破用背离识别 | 辅助/全层级 | S5 | optional |
| IND-13 | 缺口、K 线反转形态、头肩/双顶双底 | C | 形态识别 | 共振确认，不单独开仓 | 辅助/第3重 | S4 | skip |

## 三、资金管理（做成风控模块，不是技术指标）

| id | 名称 | conf | 规则 | 来源 | status |
|---|---|---|---|---|---|
| RISK-01 | 2% 法则 | A | 单笔最大亏损 ≤ 权益 2%；`仓位 = (权益*2%) / (入场价-止损价)`。**先定止损距离再算仓位**，顺序不能反 | S2 | implement |
| RISK-02 | 6% 法则 | A | 当月权益较月初回撤超 6%，本月剩余时间停止交易 | S2 | implement |
| RISK-03 | 50% 法则 | A | 有浮盈后把止损移到「入场价 + 浮盈的 50%」，保证不亏且保住一半利润 | S2 | implement |

## 四、参数待定表（没有书 → 必须做成配置项）

| 参数 | 默认值 | 备选值 | 依据 | 处理 |
|---|---|---|---|---|
| EMA 周期 | 13 | 26 | S1 明确 13 日 EMA；周线用 13 周 | 配置项 `ema_period` |
| MACD | 12, 26, 9 | 11, 25, 8（S1 提到 Elder 后续演示用值） | S1, S2 | 配置项 `macd_fast/slow/signal` |
| Force Index 平滑 | 2 日 EMA（短线）/ 13 日 EMA（中线） | 1（原始值） | S1, S2 | 配置项 `fi_ema`，默认 2，界面可切 13 |
| RSI 周期 | 14 | 7 | S4 写 7，无原书可证 | 配置项 `rsi_period`，默认 14，规格里注明「二手资料称 7」 |
| Stochastic | 13 日，阈值 30/70 | 14, 5, 3 | S1 | 配置项 `stoch_k/d/thresholds` |
| 三重滤网周期比例 | 周 / 日 / 小时（约 5:1） | 月/周/日 | S1, S2 | 配置项 `tf_high/tf_mid/tf_low` |
| 单笔风险 | 2% | 1% | S2 | 配置项 `risk_per_trade` |
| 月度熔断 | 6% | — | S2 | 配置项 `monthly_drawdown_limit` |

> **禁止**把上表任何数字硬编码进策略；`docs/indicators.yaml` 的 `params:` 是唯一入口。

## 五、不实现清单（含理由）

### Optional 未实现规则

| 条目 | 规则 | 状态 |
|---|---|---|
| IND-03 | Force Index 背离 | optional |
| IND-05 | Stochastic 穿回阈值 | optional |
| IND-09 | 量价确认 | optional |

### 排除项

| 项目 | 理由 | 来源 |
|---|---|---|
| Impulse System（K 线染绿/红/蓝） | S1 明确这是 Elder **《Come into my Trading Room》(2002)** 提出，不是 1993 年本书 | S1 |
| SafeZone、Chandelier、Market Thermometer、AutoEnvelope | S3 显示出自覆盖两本书的 MetaStock 插件；S4 混入本书清单 | S3, S4 |
| ATR(13) 止损基准、Envelope(20,±2.5%)、布林带、Keltner 作为第 3 重主力 | S4 主张，但与 S1 复述的原版第 3 重（前日高低点突破挂单）冲突，且无原书可判定 | S1 vs S4 |
| 通道触轨 + K 线反转形态作为第 3 重 | 同上，采用 SYS-05 | S1 |
| 任何 ML / LLM 预测 | 与本书方法论无关 | — |

## 六、给 Codex 的硬性要求

1. 每条都要有 `source_url + source_quote + confidence`，`source_page: null`。**禁止编造页码/章节/原文**。
2. 规格文档、代码注释、界面依据面板统一标注「基于公开资料交叉核对，非原书直引」。
3. 参数一律走配置；`status: implement` 的直接实现，`optional` 默认跳过并列清单，`skip` 不实现。
4. 若联网复核发现本表公式有误，列成「差异表」交我决策，**不要静默修改**。
5. 将来拿到书 → 跑 `prompts/P0-R.txt` 回填页码与原文，全部字段升级为 `book-confirmed`。
