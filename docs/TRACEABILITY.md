# Traceability

本文以 [docs/indicators.yaml](indicators.yaml) 的 `status`、`sources` 和公式为基准。所有规格依据均为公开资料交叉核对，非原书直引；所有 `source_page` 均为 null。

## Systems

| ID | Status | Source URL / quote | Code | Test | Signal rule_id |
|---|---|---|---|---|---|
| SYS-01 | implement | [S1](https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf)、[S2](https://www.marketsfn.com/book/trading-for-a-living) · “In his first book, 'Trading for a Living,' Elder defined his Triple Screen Trading System.” | `elder_indicators/signals.py::build_triple_screen_signals` | `tests/test_signals_and_risk.py::test_signals_include_traceability_and_follow_closed_bar_contract` | SYS-05 |
| SYS-02 | implement | [S1](https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf) · “Screen one is strict filter: no exceptions.” | `elder_indicators/signals.py::_screen_one` | `tests/test_signals_and_risk.py::test_signals_include_traceability_and_follow_closed_bar_contract` | SYS-05, direction gate |
| SYS-03 | implement | [S1](https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf)、[S2](https://www.marketsfn.com/book/trading-for-a-living) · “Elder showed that a trader could use the slope of the two most recent bars on a MACD histogram to determine the trend.” | `elder_indicators/signals.py::_screen_one`; `elder_indicators/indicators.py::calculate_indicators` | `tests/test_indicators.py::test_ema_warmup_and_hand_calculated_values`; `test_macd_line_signal_and_histogram_hand_calculated_values` | SYS-05, direction gate |
| SYS-04 | implement | [S1](https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf) · “oscillator divergences are used to buy short-term weakness in uptrends, or to sell short-term strength in downtrends” | `elder_indicators/signals.py::_screen_two` | `tests/test_signals_and_risk.py::test_signals_include_traceability_and_follow_closed_bar_contract` | SYS-05，日线预筛条件 · 🔴 见下方偏差 |
| SYS-05 | implement | [S1](https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf) · “a buy stop order to catch an upside breakout by buying at the previous day's high” | `elder_indicators/signals.py::build_triple_screen_signals` | `tests/test_signals_and_risk.py::test_signals_include_traceability_and_follow_closed_bar_contract`; `test_future_data_perturbation_does_not_change_past_signals`; `test_incomplete_same_day_daily_bar_cannot_leak_into_intraday_signal` | SYS-05 · 🔴 实际引用前第二个交易日 |

## Indicators

| ID | Status | Source URL / quote | Code | Test | Signal rule_id |
|---|---|---|---|---|---|
| IND-01 EMA | implement | [S1](https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf)、[S2](https://www.marketsfn.com/book/trading-for-a-living) · “A rising EMA confirms a bull market; a falling EMA confirms a bear market.” | `elder_indicators/indicators.py::ema`; `calculate_indicators` | `tests/test_indicators.py::test_ema_warmup_and_hand_calculated_values`; `test_elder_ray_respects_ema_warmup` | SYS-03 → SYS-05 direction context |
| IND-02 MACD | implement | [S1](https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf)、[S2](https://www.marketsfn.com/book/trading-for-a-living) · “The slope of the histogram — not its absolute level — is the primary signal.” | `elder_indicators/indicators.py::macd`; `calculate_indicators` | `tests/test_indicators.py::test_macd_line_signal_and_histogram_hand_calculated_values` | SYS-03 → SYS-05 direction context |
| IND-03 Force Index | implement | [S1](https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf)、[S2](https://www.marketsfn.com/book/trading-for-a-living) · “Force Index is calculated by subtracting yesterday's close from today's close and multiplying that by today's volume.” | `elder_indicators/indicators.py::force_index`; `calculate_indicators` | `tests/test_indicators.py::test_force_index_and_missing_volume_boundary` | SYS-05 展示参考值 |
| IND-04 Elder-Ray | implement | [S1](https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf)、[S2](https://www.marketsfn.com/book/trading-for-a-living) · “Elder Ray consists of two measures - Bull Power and Bear Power.” | `elder_indicators/indicators.py::elder_ray`; `elder_indicators/signals.py::_screen_two` | `tests/test_indicators.py::test_elder_ray_respects_ema_warmup` | SYS-04 → SYS-05 setup gate |
| IND-05 Stochastic | implement | [S1](https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf) · “Elder suggests Force Index (2-day EMA), Elder-Ray (bull/bear power), or 13-day Stochastic.” | `elder_indicators/indicators.py::stochastic`; `elder_indicators/signals.py::_screen_two` | `tests/test_indicators.py::test_stochastic_and_zero_range` | SYS-04 → SYS-05 setup gate |
| IND-06 RSI | implement | [S2](https://www.marketsfn.com/book/trading-for-a-living)、[S5](https://aloycwl.blogspot.com/2022/03/trading-for-living-alexander-elder-1993.html) · “Oscillators: Stochastic, rate of change, ... relative strength indicator, elder-ray, force index” | `elder_indicators/indicators.py::rsi`; `elder_indicators/signals.py::_screen_two` | `tests/test_indicators.py::test_rsi_flat_gain_loss_and_constant_price` | SYS-04 → SYS-05 setup gate |
| IND-09 Volume | implement | [S1](https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf)、S4（无可核验 URL） · “If the close is higher today than yesterday, the force is positive.” | `elder_indicators/indicators.py::volume`; `calculate_indicators` | `tests/test_indicators.py::test_volume_preserves_observed_values` | 无 · 日线内部字段，未出现在信号明细 |
| IND-07 Williams %R | optional, skipped | [S5](https://aloycwl.blogspot.com/2022/03/trading-for-living-alexander-elder-1993.html) · 规格未登记短引 | Not implemented | N/A | N/A |
| IND-08 Divergence classes | optional, skipped | [S5](https://aloycwl.blogspot.com/2022/03/trading-for-living-alexander-elder-1993.html) · “Class A: when price reaches a new high/low, an oscillator reaches a lower high/higher bottom” | Not implemented | N/A | N/A |
| IND-10 OBV | optional, skipped | S4（无可核验 URL）、[S5](https://aloycwl.blogspot.com/2022/03/trading-for-living-alexander-elder-1993.html) · 规格未登记短引 | Not implemented | N/A | N/A |
| IND-11 A/D and Herrick Payoff | skip | [S5](https://aloycwl.blogspot.com/2022/03/trading-for-living-alexander-elder-1993.html) · 规格未登记短引 | Not implemented | N/A | N/A |
| IND-12 Trendlines/support/resistance | optional, skipped | [S5](https://aloycwl.blogspot.com/2022/03/trading-for-living-alexander-elder-1993.html) · 规格未登记短引 | Not implemented | N/A | N/A |
| IND-13 Candlestick/chart patterns | skip | S4（无可核验 URL） · 规格未登记短引 | Not implemented | N/A | N/A |

### 规格与代码偏差

- 🔴 **SYS-05 前日价位**。日线先做 `shift(1)`，之后分钟线再以严格向后匹配获取日线。抽查三条均引用信号日前第二个交易日的 raw 高、低、收，影响突破价、止损参考和限价参考。详见 [P4 终验证据](P4_ACCEPTANCE.md)。
- 🔴 **SYS-04 / IND-03、04、05、06 日线条件**。实际 setup 是 Elder-Ray 力量回升或回落、K 值达到阈值、RSI 达到阈值三者任一成立。规格中的 Force Index 背离、Stochastic 穿回阈值及 Elder-Ray 完整确认条件未接入。Force Index 值随信号输出，原始成交量保留在日线计算中。
- 🔴 **IND-09 量能确认**。数值测试覆盖原始成交量透传。规格中的量价确认未参与信号。
- **SYS-05 来源字段**。BUY 引用 S1 的 “buy stop order to catch an upside breakout”。SELL 引用 S1 的 “sell short-term strength in downtrends”，对应 SYS-04 的日线原则。两者在信号 CSV 中均标为 SYS-05。

## Risk

| ID | Status | Source URL / quote | Code | Test | Signal rule_id |
|---|---|---|---|---|---|
| RISK-01 2% rule | implement | [S2](https://www.marketsfn.com/book/trading-for-a-living) · “Never risk more than 2% of total trading capital on a single trade.” | `elder_indicators/risk.py::position_size`; `presentation/dashboard.py::estimate_position` | `tests/test_signals_and_risk.py::test_risk_rules_and_lot_rounding`; `tests/test_presentation.py::test_position_estimate_requires_equity_and_rounds_to_board_lot` | Applied when displaying SYS-05 BUY; not a signal trigger |
| RISK-02 6% halt | implement | [S2](https://www.marketsfn.com/book/trading-for-a-living) · “If the account falls 6% below its monthly opening balance, stop trading for the rest of that month.” | `elder_indicators/risk.py::monthly_halt` | `tests/test_signals_and_risk.py::test_risk_rules_and_lot_rounding` | N/A, account-level guard |
| RISK-03 50% protection | implement | [S2](https://www.marketsfn.com/book/trading-for-a-living) · “the stop is moved to a level that protects at least half the paper gain” | `elder_indicators/risk.py::protected_stop` | `tests/test_signals_and_risk.py::test_risk_rules_and_lot_rounding` | N/A, position-management output |

## Provenance Checks

- Signal CSV columns include `rule_id`, `source_url`, `source_quote`, `confidence`, and `source_page`.
- The P3 detail panel displays the fixed notice “依据：公开资料交叉核对，非原书直引”.
- CSV 的 `source_page` 非空数为 0。展示 payload 未包含该字段。
