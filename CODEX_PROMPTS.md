# 《以交易为生》交易软件 — Codex 提示词包（无电子书模式 / Mode B）

**目标产品**：加载行情 → 按《以交易为生》(Alexander Elder, *Trading for a Living*) 的指标体系计算 → 在 K 线上标出买卖点 → 每个信号可追溯到依据来源。

**当前模式：Mode B — 用户没有这本书的电子版。** 已据此改写全流程。

---

## 0. Mode B 的四条规则（最重要，先读）

原方案 P0 是「从书的电子版逐条提取指标」。没有电子书时这一步会卡死，且 P2 里「只实现 confirmed 条目」会导致一个指标都实现不了。所以现在改为：

| # | 规则 |
|---|---|
| 1 | **事实源换成 `INDICATOR_SPEC.md`**（本包内，公开资料交叉核对规格 v1.0），由 P0 规范化为 `docs/INDICATORS.md`。不再要求从书提取。 |
| 2 | **绝不伪造书中出处。** 用户没有书 → 禁止输出书页码、章节号，禁止写「书中原文」「原著写道」等表述，禁止编造引文。溯源锚点统一为：`source_url + source_quote(≤50字) + confidence(A/B/C)`；`source_page` 字段一律为 `null`。 |
| 3 | **来源必须诚实标注**：每个信号/界面上都写明「依据：公开资料交叉核对，非原书直引」。规格文档顶部也要写这句话。 |
| 4 | **所有参数可配置。** 没有书就没有唯一权威参数值（RSI 7 还是 14、Stochastic 周期、Force Index 用 2 日还是 13 日 EMA 都有分歧），因此参数一律从配置读取，默认值取规格表，禁止硬编码、禁止「按行业惯例」自行选定。 |

> 将来若拿到书，跑 `prompts/P0-R.txt`（回填模式）一次性补页码与原文，把 confidence 升级为 `book-confirmed`。设计上已留好口子，现在不用管。

**事实源层级**：`INDICATOR_SPEC.md`（人读，核对基准） → `docs/INDICATORS.md` + `docs/indicators.yaml`（P0 产出，机器可读，代码只认这个） → 代码。

---

## 1. 本机环境与启动方式（已实测）

| 工具 | 状态 |
|---|---|
| `codex` CLI | ✅ 0.169.0，`codex exec` 非交互模式可用，会自动加载仓库根目录的 `AGENTS.md` |
| `git` | ✅ 已装；`codex exec` 默认要求 git 仓库，本目录已 `git init` |
| `python3` | ✅ 3.13 |
| `gh` | ❌ **未安装** → P1 改用 `curl` 调 GitHub REST API（命令见第 5 节），提示词里已让 Codex 自动判断 |

**在这个目录直接跑**（每条提示词都是独立 txt，不用手动复制）：

```bash
cd /Users/kaixin/WorkBuddy/2026-11-20-21-16-17/codex-elder-trading

# 顺序：P0 与 P1 可并行/任意先后，但 P2 之前必须都完成
codex exec --sandbox workspace-write "$(cat prompts/P0.txt)"     # 核定规格
codex exec --sandbox workspace-write "$(cat prompts/P1.txt)"     # GitHub 选型
codex exec --sandbox workspace-write "$(cat prompts/P2.txt)"     # 实现（自动读 PROJECT_SELECTION.md）
codex exec --sandbox workspace-write "$(cat prompts/P3.txt)"     # 界面 + 买卖点
codex exec --sandbox workspace-write "$(cat prompts/P4.txt)"     # 验收
```

- 若 Codex 报网络受限，把 `--sandbox workspace-write` 换成 `--sandbox danger-full-access`（仅在你确认时）。
- 想看它最后说了什么，加 `-o /tmp/p0-summary.txt`。
- 交互式用 `codex` 直接打开，粘贴 `prompts/P0.txt` 的内容即可。

**五条实操**（决定成败）：
1. 在**仓库根目录**启动 Codex，让它看到真实文件和真实报错。
2. 每个阶段先让它**输出计划、等你确认再改代码**（P0 只写文档，可直接跑）。
3. 铁律已写进 `AGENTS.md`，不用每条 prompt 重复贴；但遇到它想「按常见做法」补参数时，直接回：「查 docs/INDICATORS.md，查不到就标 todo 问我」。
4. 每阶段结尾索要**证据**：pytest stdout、命令输出、CSV 样例、图、diff。不接受「已完成」。
5. 每阶段一个 `git commit`，跑偏能回滚。

### 1.1 本机运行实录（2026-11-20，已实测）

我用本机 `codex exec` 真跑过 P0，结果如下，**你需要知道**：

| 尝试 | 结果 |
|---|---|
| `codex exec --sandbox workspace-write "$(cat prompts/P0.txt)"` | Codex 正常启动（模型 `gpt-6.2-sol`，provider custom），但本地命令被拦截：`sandbox_apply: Operation not permitted` → 读不到 `INDICATOR_SPEC.md`、写不了 `docs/`。**它没有凭空编规格，直接停下报权限问题**，说明 AGENTS.md 的约束生效了。 |
| `--sandbox danger-full-access` + 把规格内联进 prompt | 进程被 SIGTERM（exit 137），仍无产出。 |

判断：这是**我这层执行环境的沙箱与 Codex 自带沙箱叠加**造成的，不是提示词的问题。你在自己的终端 / Codex IDE 插件 / 桌面端里直接跑，通常不会有这个限制。

**因此 P0 已由我代跑完成**，产出已落盘：
- `docs/INDICATORS.md`（人读，21 条规格）
- `docs/indicators.yaml`（机器可读，`params:` 集中）

`source_page` 全为 `null`，没有伪造任何书内定位。**P2 现在可以直接读 `docs/indicators.yaml`，不用再跑 P0。** 从 P1 开始即可：

```bash
cd /Users/kaixin/WorkBuddy/2026-11-20-21-16-17/codex-elder-trading
codex exec --sandbox workspace-write "$(cat prompts/P1.txt)"   # 选型
codex exec --sandbox workspace-write "$(cat prompts/P2.txt)"   # 实现
codex exec --sandbox workspace-write "$(cat prompts/P3.txt)"   # 界面
codex exec --sandbox workspace-write "$(cat prompts/P4.txt)"   # 验收
```

若你自己的终端也报 `sandbox_apply: Operation not permitted`：
1. 改用交互式：`codex`（不带 `exec`），粘贴 `prompts/P1.txt` 内容；
2. 或用 Codex IDE 插件 / 桌面端，它们不走 CLI 的 seatbelt 沙箱；
3. 或检查 `~/.codex/config.toml` 的 `sandbox_mode` / `approval_policy` 设置。

### 1.2 已定技术路线（2026-11-20 用户拍板）：路线 1 · 最小改动原型

用户在三条备选里选了**路线 1「原型起步」**：clone 选中的框架，只新增策略适配文件 + 独立指标模块 + 配置；买卖点用框架图表或 `setMarkers`；**不重写**框架的数据/回测层。指标与信号引擎写成框架无关模块，验证通过后换自建前端即可升级为完整自有软件。（注意：最终选定的 VN.py 没有内置未来函数审计工具，见 1.4 节。）

据此已同步修改 `AGENTS.md`、`prompts/P1.txt`、`prompts/P2.txt`：P1 不再输出三条备选，改为主攻策略/回测框架方向并给出具体仓库的 clone 路径与策略文件位置；P2 增加「独立指标模块」的架构约束。

**P1 选型已关闭**：底座已定为 **VN.py**（见 `PROJECT_SELECTION.md` 与 1.4 节），P2 已实现、长区间 A 股信号已验收。仍待用户决策的只剩：RSI 周期（默认 14 还是二手资料的 7）、optional 指标是否纳入后续版本；**目标市场已定为 A 股**（见 1.4 节）。

### 1.3 curl 检索实测（2026-11-20，已跑通）

`gh` 未装，但第 5 节的 `curl` 命令**真实可用**，返回 12 个仓库，原始 JSON 已存 `docs/github-candidates.json`：

| 仓库 | star | 最近 push | 许可 |
|---|---|---|---|
| freqtrade/freqtrade | 57,098 | 2026-11-19 | **GPL-3.0** |
| ccxt/ccxt | 44,930 | 2026-11-20 | MIT |
| hummingbot/hummingbot | 21,306 | 2026-11-20 | Apache-2.0 |
| jesse-ai/jesse | 8,823 | 2026-11-17 | **MIT** |
| Drakkar-Software/OctoBot | 6,962 | 2026-11-19 | GPL-3.0 |
| coding-kitties/investing-algorithm-framework | 2,251 | 2026-11-17 | Apache-2.0 |

⚠️ **许可证提醒（路线 1 是 fork，影响更大）**：freqtrade / OctoBot 是 **GPL-3.0**，fork 后衍生作品通常也要按 GPL 开源；若计划闭源或商用，优先评估 **jesse（MIT）**、**hummingbot / investing-algorithm-framework（Apache-2.0）**。P1 已要求在报告里逐条标出许可证并说明对「自有产品」的影响。

> 这只是**原始检索快照**，不是选型结论。打分、多周期能力证据、clone 路径仍由 Codex 在 P1 里完成。

### 1.4 目标市场确定为 A 股（2026-11-20 23:00 用户确认）

用户明确要跑 **A 股（沪深）**，不是加密货币。这是选型的根本输入，已做以下改动：

- `AGENTS.md` 写入 A 股规则：数据源 akshare/baostock、复权口径、T+1、涨跌停、100 股手数、沪深交易日历、停牌、三重滤网周期映射（周/日/60 分钟）。
- `docs/indicators.yaml` 新增 `market:` 配置节；铁律 3 改为「参数从 `params:` 与 `market:` 读取」。
- `prompts/P2.txt` 加 A 股数据适配层与联网边界（二选一决策已完成，现为 VN.py 直接实现）；`P3.txt` 加 A 股界面元素；`P4.txt` 加 A 股专项验收；`P1.txt` 新增硬约束 F「A 股数据源适配」，供任何后续重跑使用。
- `PROJECT_SELECTION.md` 已按 A 股目标整体刷新为增量复核报告，并于 2026-11-20 23:44 记录用户确认 VN.py 底座。
- **本文件下方的 P2/P3/P4 代码块是初始快照**，实际执行一律以 `prompts/*.txt` 为准（已含 A 股约束）。

✅ **决策已完成（2026-11-20 23:44 用户确认）**：A 股增量复核后选定 **VN.py**（vnpy/vnpy + vnpy_ctastrategy + vnpy_ctabacktester，MIT）。Jesse 因加密撮合规则（7×24、无涨跌停、无 T+1）与 A 股不符被排除；RQAlpha 商用/法人使用需米筐授权、PyBroker LICENSE 含 Commons Clause，均已淘汰。

- VN.py 没有内置 `lookahead-analysis` 类未来函数审计工具，P2/P4 用代码审查 + 未来数据扰动测试替代。
- 产品侧负责 A 股行情适配（akshare → 本地缓存）、T+1、涨跌停、整手约束与周/日/60 分钟周期聚合；框架只作依赖。
- 选型环节已关闭：`prompts/P2.txt`、`AGENTS.md`、`PROJECT_SELECTION.md` 均已同步为「底座已确认、直接开始实现」，不会再重开方案对比或停下来问底座。

---

## 2. 选型硬约束（让 Codex 自己搜，别替它定死）

**不满足 A 直接淘汰**：
- **A. 必须支持多时间框架**（周线 / 日线 / 小时线同时参与一个信号）——三重滤网没这个等于没实现。要求到仓库文档/源码找证据（freqtrade 的 `@informative` / `merge_informative_pair`、backtrader 的多 data feed），把证据路径写进报告。
- **B. 允许自定义指标公式**；**C. 能把买卖信号标到 K 线上**；**D. 许可证允许二次开发、近 12 个月有提交、未 archived**。
  - 路线 1 是 fork，需特别区分 GPL-3.0（传染性）与 MIT / Apache-2.0，详见 1.3 节。
- **E（Mode B 新增）：参数可外部配置**，不能把周期写死在策略里。

三类方向各找 2~3 个：策略/回测框架（freqtrade、backtrader、vectorbt、jesse、vn.py）、图表界面（lightweight-charts 系、FreqUI）、指标计算库（TA-Lib、pandas-ta、technical）。

⚠️ 选型期历史备注（当前底座为 VN.py，此条不再适用）：Freqtrade 官方把 `plot-dataframe` / `plot-profit` 标记为 **deprecated**、推荐 FreqUI（https://www.freqtrade.io/en/stable/plotting/）。别在废弃命令上花时间。

**打分维度（1~5）**：多周期 / 自定义指标 / 买卖点可视化 / 回测 / 活跃度 / 二次开发成本 / 与 Python+pandas 契合 / **最小改动成本（路线 1 重点）** → 加权总分 → 选 1 个 + 200 字理由 + 淘汰原因。

> 路线 1 已定，P1 不再输出三条备选；改为给出落地信息（clone 命令、本地目录、策略文件路径、P2 该引用的底座）。

---

## 3. 六条提示词（正文；可直接用的纯文本在 `prompts/` 目录）

### P0 — 核定规格，产出唯一事实源（无电子书版）

```
你是这个仓库的技术负责人。做一个以《以交易为生》(Alexander Elder, Trading for a Living, 1993) 方法论为依据的交易软件。

重要前提：用户没有这本书的电子版。禁止编造书页码、章节号或"书中原文"；所有依据锚定公开来源 URL + 短引文 + 置信度。

输入：仓库根目录的 INDICATOR_SPEC.md（公开资料交叉核对规格 v1.0）。这是唯一输入。

任务：把它规范化成机器可读规格，产出 docs/INDICATORS.md 与 docs/indicators.yaml。
每条必须包含：
- id（IND-xx / SYS-xx / RISK-xx）
- 中文名 / 英文名
- 数学公式（LaTeX 或伪代码，写清所有参数）
- 参数：默认值 + 可选范围 + 是否有分歧（分歧项列进"参数待定表"）
- 输入数据（需要 open/high/low/close/volume 中哪些）
- 层级：三重滤网第几重 / 趋势 / 振荡 / 量能 / 风控
- 买卖规则：可直接翻译成代码的布尔条件
- confidence：A（多来源交叉确认）/ B（二手整理）/ C（默认不实现）
- source_url + source_quote（<=50 字）+ source_page: null
- status：implement / optional / skip

额外要求：
1. 若环境可联网，逐条用至少 2 个独立公开来源复核 A 级条目的公式，把 URL 和引文补进表；复核不了标 unverified，不要删除条目。
2. 汇总"参数待定表"：RSI 周期、Stochastic 周期、Force Index 平滑周期、MACD(12,26,9)、EMA(13)、三重滤网周期比例。每项给默认值、备选值、依据来源。代码里这些必须做成配置项。
3. 明确区分"多来源交叉确认"与"二手整理"，不许把二手内容写成"书中原文"。
4. C 级条目（Impulse System、SafeZone、Chandelier、AutoEnvelope、ATR 通道体系等）归入"不实现清单"并说明理由。
5. 文档与代码顶部统一标注："本规格基于公开资料交叉核对重建，非原书直引；source_page 一律为 null。"
6. docs/indicators.yaml 要能被代码直接读取，参数集中在 params: 下，禁止散落硬编码。
7. 本阶段只写文档，不改任何代码。

完成后输出：条目总数、A/B/C 各多少、参数待定表全文、不实现清单、两个文件路径。
```

### P1 — 在 GitHub 找契合的底座并给出证据

```
目标：为产品选一个可二次开发的开源底座，调研必须可复现。已定技术路线：路线 1「最小改动原型」（clone 框架 + 策略文件 + 独立指标模块，不再给三条备选让用户选）。

0. 先检查 gh CLI 是否可用（command -v gh）。不可用则改用 curl 调 GitHub REST API，命令见 CODEX_PROMPTS.md 第 5 节。不许凭记忆推荐仓库。

1. 真实检索 GitHub，主攻「策略/回测框架」方向（freqtrade / backtrader / vectorbt / jesse / vn.py）；图表界面库与指标计算库只作为买卖点渲染、指标计算的补充依赖评估。把检索命令原文和返回结果贴进报告。
2. 硬约束（不满足直接淘汰并写明原因）：
   A. 支持多时间框架（周/日/小时同时参与一个信号）——到仓库文档/源码找证据并写路径（freqtrade 的 @informative / merge_informative_pair，backtrader 的多 data feed）。
   B. 允许自定义指标公式。
   C. 能把买卖信号标到 K 线上（箭头/marker/交易点表）。
   D. 许可证允许二次开发，近 12 个月有提交，未 archived。特别区分：GPL-3.0 有传染性（fork 后衍生作品通常须同样开源），路线 1 是 fork，报告里必须逐个标出许可证并说明对自有产品的影响，优先 MIT / Apache-2.0。
   E. 指标参数可外部配置，不写死。
3. 每个候选取真实数据：star 数、最近 push、license、主语言、archived 状态、issue/PR 活跃度。
4. 注意 Freqtrade 已弃用 plot-dataframe、推荐 FreqUI，不要基于废弃能力打分。
5. 输出 PROJECT_SELECTION.md：检索命令、>=5 个候选对比表、7 维度打分 1-5、加权总分、最终选 1 个 + 200 字理由、淘汰项及原因。
6. 路线已定，不要再给三条备选。改为输出「落地信息」：最终选定仓库的完整 clone 命令、clone 到哪个本地目录、策略文件应放在该框架的哪个路径、配置怎么改、以及 P2 该引用哪个底座路径。并确认该框架是否自带未来函数检查工具（如 freqtrade 的 lookahead-analysis）。

本阶段不要 clone、不要改代码，先交报告。
```

### P2 — 实现指标与三重滤网信号引擎

```
承接 P0/P1。先读取 PROJECT_SELECTION.md，取其中"最终选定"的仓库与本地路径作为底座；若该文件不存在或没有明确结论，停下来问我，不要自己假设。

读取 docs/INDICATORS.md 与 docs/indicators.yaml：只实现 status=implement 的条目；optional/unverified/skip 一律跳过并在 README 的"未实现清单"列出。

1. 先输出实现计划（目录结构、每个指标放哪、如何接到底座策略接口、测试策略），等我确认后再写代码。
2. 每个指标实现为纯函数 fn(df: pd.DataFrame, **params) -> pd.Series/DataFrame，只用 pandas/numpy；不读网络、不绘图、不依赖 UI。参数一律从 docs/indicators.yaml 的 params 读取，禁止硬编码、禁止自行调参。
3. 每个指标配单元测试：5~10 行手工构造 OHLCV，把期望值手算出来做数值断言；覆盖 EMA 预热期、成交量缺失、NaN 边界、常数价格序列。
4. 三重滤网引擎：第 1 重定方向 -> 第 2 重找逆势回调 -> 第 3 重突破挂单。第 1 重方向是严格开关，逆势信号一律丢弃。
5. 风控模块：2% 法则仓位（先定止损距离再算仓位）、6% 法则月度熔断、50% 法则移动止损。
6. 信号表每行必须携带：timestamp, symbol, side, price, rule_id, indicator_values(dict), source_url, source_quote, confidence, source_page(null)。缺来源的信号不许生成。
7. 严禁：未收盘 K 线、shift(-n)/任何未来数据、逐行 for 循环算指标、把二手参数当原著参数、引入机器学习预测、伪造书页码。

完成后运行 pytest 并贴真实输出；列出实现/跳过了哪些 id 及原因。
```

### P3 — 把买卖点标出来，做成能看的软件界面

```
把 P2 已验收的 A 股买卖点渲染成人能看懂的交易软件界面。

底座已确认：VN.py（vnpy/vnpy + vnpy_ctastrategy + vnpy_ctabacktester，MIT）。
不要再重新选型、不要提出方案对比、不要停下来问底座。产品代码留在 codex-elder-trading/，
VN.py 只作上级目录依赖，禁止把框架源码复制进产品仓库。

输入：data/cache/600519_SH_*_{qfq,raw}.csv 与 examples/signals.csv（120 条信号，P2 已验收 17 passed）。
本阶段只做展示层：不要重新计算信号，不要改动 elder_indicators/ 与 market_data/。

1. 主图 K 线 + EMA；副图 MACD 柱状图 / Force Index / Elder-Ray / RSI。参数只读 docs/indicators.yaml 的 params: 与 market:，禁止硬编码周期或市场规则。
2. 买点：K 线下方箭头 + 标签（rule_id 与触发规则）；卖点：上方箭头。点击/悬停展示完整依据：rule_id、source_quote、source_url、confidence、触发时各指标数值、按 2% 法则算出的仓位与止损价。
3. 每个依据面板顶部固定一行："依据：公开资料交叉核对，非原书直引"。禁止显示书页码、"书中原文""原著写道"；source_page 为 null 不得渲染成任何书内定位。
4. 渲染方案二选一并给出理由：用 VN.py 的 K 线图表组件（vnpy_ctabacktester 的 CandleChartDialog / 成交点标注）做桌面端，或产品侧自建 lightweight-charts 前端用 setMarkers 导出可打开的 HTML。不要引入新的第三方框架底座。
5. 导出可打开的 HTML 快照或静态图，更新 examples/（保留已有 signals.csv 与 signal-validation.html，新增界面产物），并给出可复现的生成命令。
6. 配色遵循中国市场惯例：涨红跌绿；货币符号默认 ¥；界面顶部固定："仅供研究与回测，不构成投资建议"。
7. A 股界面元素：股票代码与名称（如 600519.SH / 贵州茅台）、涨跌幅、涨跌停标记、停牌日留白，按沪深交易日历显示；信号面板额外显示该股当日是否触及涨跌停（触及则标注「可能无法成交」，不要静默当作成交）。
8. 保持框架无关：界面层只读 signals.csv / 缓存 CSV 与 docs/indicators.yaml，不得把框架专属 API 引入指标引擎。

先给界面草图/组件结构再写实现，等我确认后再写代码；完成后给截图或 HTML 路径及生成命令、pytest 输出、diff 与 git commit。
```

### P4 — 验收与交付（要证据，不要结论）

```
做一次完整验收，逐项给证据，不接受"已完成""应该没问题"。

1. 跑通"数据加载 -> 指标计算 -> 信号 -> 出图"的一条命令，贴命令和真实 stdout。
2. pytest 全绿，贴用例数与输出；确认每个 implement 指标都有数值断言测试。
3. 未来函数检查：VN.py 无内置审计工具，用代码审查（grep `shift(-n)`、未收盘 K 线）+ tests/ 已有的未来数据扰动测试 `test_future_data_perturbation_does_not_change_past_signals` 证明只用已收盘数据，贴 pytest 真实输出。
4. 抽 3 个买卖点，逐个对照 docs/INDICATORS.md 的公式与 source_quote，说明触发原因、属于第几重滤网、止损价与 2% 仓位怎么算的。同时确认没有任何一处出现伪造的书页码。
5. 生成 docs/TRACEABILITY.md：id -> source_url/quote -> 代码文件/函数 -> 测试用例 -> 信号 rule_id。对不上就标红说明。
6. README：安装运行、目录说明、参数在哪改、已知限制、未实现清单、"非原书直引"声明、风险声明。
7. A 股专项验收：复权价连续性检查、停牌日不产生信号、涨跌停无法成交的买点应标记而非静默成交、T+1 约束、周线与 60 分钟线由日线/分钟线正确构造（每日 4 根）、沪深交易日历对齐；逐项贴检查结果。
8. git 提交，message 写清范围。

最后 5 行总结：实现了什么、验证了什么、还差什么、下一步建议、需要我决策的问题。
```

### P0-R — 纸质书回填（Mode B-P，当前阶段）

> **状态（2026-11-21 20:03）**：用户只有纸质书，已拍来 100 张书页照片，
> 已逐行确认 `docs/book_references.csv` 的 44 行引文草稿与版本字符串（三批：17:42 确认 32 行、19:22 确认 9 行、20:03 确认 RISK-03 3 行）；
> 差异表 D1~D11 已全部「按建议」拍板（D9 趋势线降级、D10 维持 skip、D11 浮盈保护比例保持 0.50），见 `docs/BOOK_BACKFILL_DECISIONS.md`。
> 完整可执行提示词见 **`prompts/P0-R.txt`**（最终轮合并版：第二、三批一次回填，直接发给 Codex，不要再给计划、不要再问）。
> 累计覆盖 **19 条 / 44 行**，仍为 null 的只剩 2 条（IND-04、IND-07，第 2 版正文无独立小节，永久保留）；全局「非原书直引」提示保留。

```
用纸质《以交易为生》（原书第2版，机工社 2017.6 第1版 / 2020.6 第8次印刷，
ISBN 978-7-111-56972-5）回填书内定位。事实源只能是 docs/book_references.csv
中用户已确认的行与 docs/book_photos/ 照片，逐字抄用，禁止推断或编造页码。
已确认条目新增 book_confirmed/book_edition/book_chapter/book_page/book_quote
字段并把 source_page 改为真实页码；保留原 confidence: A（信号里硬编码为 A，
覆写会挂 28 项测试）。不改指标/信号/风控代码、不重新生成 signals.csv、
不改 params:/market: 数值。D1~D11 差异已由用户拍板，不要重新列差异表。
同步 docs/INDICATORS.md、docs/indicators.yaml、INDICATOR_SPEC.md、
docs/TRACEABILITY.md 及「已确认条目填真实页码、未确认条目保持 null」的部分回填口径；
界面仅对已确认条目追加「书内确认：《以交易为生》（原书第2版）第 X 章 第 Y 页」。
完成后给：回填行数 / 待补行数 / diff / pytest 28 passed / git commit。
```

---

## 4. 验收总清单

- [ ] `docs/INDICATORS.md` 每条都有 `source_url + source_quote + confidence`；Mode B 阶段 `source_page` 全为 null，P0-R 部分回填后仅已确认条目填真实页码、其余仍为 null
- [ ] 全仓库 grep 不到编造的"书中原文/第 X 章/第 X 页"表述
- [ ] `docs/indicators.yaml` 的 params 集中可配，代码里没有硬编码周期数字
- [ ] `PROJECT_SELECTION.md` 有真实 API 返回，选型满足 A~E
- [ ] 每个 implement 指标有手算数值单测
- [ ] 三重滤网三层齐全，第 1 重是硬开关
- [ ] `signals.csv` 每行都能追到 `rule_id + source_url + quote + confidence`
- [ ] 图上有买卖箭头，点开能看到依据与"非原书直引"标注
- [ ] 未来函数检查通过；`TRACEABILITY.md` 全链路对得上

---

## 5. 附录：GitHub 检索命令（`gh` 未装时用 curl）

```bash
# 方案 A：装 gh（可选）
brew install gh && gh auth login
gh search repos "algorithmic trading" --stars ">3000" --language python \
  --json fullName,stargazersCount,description,url,updatedAt --limit 30

# 方案 B：不装 gh，直接 REST API（推荐，本机可直接跑）
curl -sS -H "Accept: application/vnd.github+json" \
  "https://api.github.com/search/repositories?q=trading+bot+technical+indicator+stars:%3E2000+language:python+pushed:%3E2025-01-01&sort=stars&per_page=20" \
  | python3 -c "import sys,json; [print(f\"{i['full_name']} | star={i['stargazers_count']} | push={i['pushed_at']} | archived={i['archived']} | {i['html_url']}\") for i in json.load(sys.stdin)['items']]"

# 单个仓库真实状态
curl -sS https://api.github.com/repos/freqtrade/freqtrade \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print({k:d.get(k) for k in ('full_name','stargazers_count','pushed_at','archived','license','language')})"

# 多周期能力证据（clone 后自己 grep）
# freqtrade: @informative / merge_informative_pair
# backtrader: 多个 cerebro.adddata()
```

> 未认证的 GitHub API 限流 60 次/小时，够用；若超限，等一小时或 `gh auth login` 后走认证。

---

**风险声明**：本书方法提出于 1993 年，且本规格是公开资料重建、非原书直引，公式与参数务必在你的市场与周期上重新验证。软件定位为研究与回测工具，默认 Dry-run，不构成投资建议。
