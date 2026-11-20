# AGENTS.md — 《以交易为生》交易软件 项目约定

> Codex 会自动加载本文件。以下规则优先级高于任何「常见做法」或模型记忆。

## 项目目标

做一个交易软件：加载 OHLCV 行情 → 按《以交易为生》(Alexander Elder, *Trading for a Living*) 的指标体系计算 → 在 K 线上标出买卖点 → 每个信号可追溯依据。

## 当前模式：Mode B（用户没有这本书的电子版）

- 唯一事实源：`INDICATOR_SPEC.md`（公开资料交叉核对规格 v1.0）→ P0 规范化为 `docs/INDICATORS.md` + `docs/indicators.yaml` → 代码只读 `docs/indicators.yaml`。
- **本规格不是原书直引。** 所有 `source_page` 为 `null`。
- 溯源格式固定为：`source_url + source_quote(≤50字) + confidence(A/B/C)`。
- **严禁编造**：书页码、章节号、"书中原文""原著写道"等表述、任何引文。全仓库不得出现伪造的书内定位。
- 规格文档、代码注释、界面依据面板统一标注：「依据：公开资料交叉核对，非原书直引」。

## 五条铁律

1. **禁止凭模型记忆补公式或参数。** 缺信息就标 `todo` 并询问用户，不许用「行业惯例」「通常取 14」之类理由自行决定。
2. **每个买卖信号必须可追溯**：`rule_id + source_url + source_quote + confidence + indicator_values`。没来源的信号不许生成。
3. **所有参数可配置**：从 `docs/indicators.yaml` 的 `params:` 读取，禁止把周期数字硬编码进策略。参数分歧见规格第四节「参数待定表」。
4. **只用已收盘 K 线**：禁止 `shift(-n)`、未来数据、repaint。指标与信号用向量化 pandas，禁止逐行 for 循环。
5. **按 status 实现**：`implement` 才写，`optional` 默认跳过并列进 README 未实现清单，`skip` 不实现。

## 架构硬约束：三重滤网

三层必须齐全，且第 1 重方向是**严格开关**（逆势信号一律丢弃）：
- 第 1 重（高周期，默认周线）：13 EMA 斜率 + MACD 柱状图最近两根柱斜率 → 定多空方向
- 第 2 重（中周期，默认日线）：Force Index / Elder-Ray / Stochastic / RSI 找逆大势的回调与背离
- 第 3 重（低周期，默认小时）：突破昨日最高价挂 buy stop / 跌破昨日最低价挂 sell stop

选型与实现都必须支持**多时间框架**（周/日/小时同时参与一个信号），否则不符合要求。

风控模块：2% 法则（先定止损距离再算仓位）、6% 法则月度熔断、50% 法则移动止损。

## 中国区约定

- 涨 = 红，跌 = 绿（与欧美相反）。
- 货币符号默认 ¥。
- 界面顶部固定：「仅供研究与回测，不构成投资建议」。

## 工作方式

- 每个阶段**先输出计划，等用户确认后再改代码**（纯文档阶段除外）。
- 每阶段结束必须给**证据**：pytest 真实 stdout、命令输出、CSV 样例、图表文件、diff。不接受「已完成」「应该没问题」。
- 每阶段一个 `git commit`，message 写清范围。
- `gh` CLI 未安装：检索 GitHub 用 `curl` 调 REST API（命令见 `CODEX_PROMPTS.md` 第 5 节），不许凭记忆推荐仓库。
- 已核实：Freqtrade 的 `plot-dataframe` / `plot-profit` 已 deprecated，用 FreqUI 或 lightweight-charts 的 `setMarkers`。

## 阶段顺序

`prompts/P0.txt`（规格）与 `prompts/P1.txt`（选型）可并行；`P2`（实现）前两者必须都完成；之后 `P3`（界面）→ `P4`（验收）。将来拿到书再跑 `P0-R.txt` 回填。

## 风险

方法出自 1993 年且本规格为公开资料重建，参数需在目标市场重新验证。默认 Dry-run / 回测，不接实盘资金，不构成投资建议。
