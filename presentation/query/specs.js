/* Synchronized from docs/indicators.yaml. Keep values and citations aligned there. */
window.ELDER_SPEC = {
  params: {
    ema_period: 13, macd_fast: 12, macd_slow: 26, macd_signal: 9,
    fi_ema: 2, rsi_period: 14, stoch_k: 13, stoch_d: 3,
    oversold: 30, overbought: 70, breakout_offset_ticks: 1,
    risk_per_trade: 0.02, monthly_drawdown_limit: 0.06,
    profit_protect_ratio: 0.50
  },
  market: {
    trading_sessions: {
      morning_open: "09:30", morning_close: "11:30",
      afternoon_open: "13:00", afternoon_close: "15:00"
    },
    board_limit_pct: {main_board: 0.10, chinext: 0.20, star_market: 0.20,
      beijing_stock_exchange: 0.30, st: 0.05},
    board_code_prefixes: {
      main_board: ["600", "601", "603", "605", "000", "001", "002", "003"],
      chinext: ["300", "301"], star_market: ["688", "689"],
      beijing_stock_exchange: ["4", "8", "920"]
    },
    min_lot: 100, price_tick: 0.01, t_plus_1: true, cash_only: true,
    allow_short: false
  },
  provenance: "依据：公开资料交叉核对，非原书直引",
  rules: {
    "SYS-02": {
      source_url: "https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf",
      source_quote: "Screen one is strict filter: no exceptions.", confidence: "A",
      book_confirmed: "第2版", book_page: ["p.229", "p.113"],
      book_quote: ["在上升的趋势里只允许你选择买入或者观望；在下跌的趋势里只允许你卖出或观望。", "当EMA走平，只是小幅波动时，那意味着一种漫无目的、没有趋势的市场。这种情况下不要使用趋势跟随方法。"]
    },
    "SYS-03": {
      source_url: "https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf",
      source_quote: "Elder showed that a trader could use the slope of the two most recent bars on a MACD histogram to determine the trend.", confidence: "A",
      book_confirmed: "第2版", book_page: ["p.228"], book_quote: ["MACD的斜率由最近两根MACD柱线之间的关系确定。"]
    },
    "SYS-04": {
      source_url: "https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf",
      source_quote: "oscillator divergences are used to buy short-term weakness in uptrends, or to sell short-term strength in downtrends", confidence: "A",
      book_confirmed: "第2版", book_page: ["p.229", "p.230", "p.143"],
      book_quote: ["将震荡指标应用于日线图之中。", "当周趋势是上升的，三重滤网仅允许采用日线图震荡指标发出的买入信号，而不会允许采用其发出的卖出信号。", "三重滤网交易系统只有当周趋势向上时，随机指标给出的买入信号才会被采用。"]
    },
    "SYS-05": {
      source_url: "https://cmtassociation.org/wp-content/uploads/2025/08/MTA04May.pdf",
      source_quote: "a buy stop order to catch an upside breakout by buying at the previous day's high", confidence: "A",
      book_confirmed: "第2版", book_page: ["p.231", "p.236", "p.232"],
      book_quote: ["做多时，在日线向上突破前一交易日高点的时候买入；卖空时，在日线向下突破前一交易日低点的时候卖出。", "三重滤网交易系统需要设置相对保守的止损价位。", "突破技术仍然是有效的，但是我很少使用它了。"]
    },
    "RISK-01": {
      source_url: "https://www.marketsfn.com/book/trading-for-a-living",
      source_quote: "Never risk more than 2% of total trading capital on a single trade.", confidence: "A",
      book_confirmed: "第2版", book_page: ["p.296", "p.298"],
      book_quote: ["2%原则会防止你的账户在单次交易中出现本金亏损2%以上的风险。", "将A除以B，得到所能交易的最大股数。"]
    },
    "RISK-02": {
      source_url: "https://www.marketsfn.com/book/trading-for-a-living",
      source_quote: "If the account falls 6% below its monthly opening balance, stop trading for the rest of that month.", confidence: "A",
      book_confirmed: "第2版", book_page: ["p.302", "p.304"],
      book_quote: ["6%原则能给每一个账户都设了一个当月最大回撤比例。", "如果两者之和已经超过你月初账户资产的6%时，这个月剩下的时间你都不能再增加交易头寸了"]
    },
    "RISK-03": {
      source_url: "https://www.marketsfn.com/book/trading-for-a-living",
      source_quote: "the stop is moved to a level that protects at least half the paper gain", confidence: "A",
      book_confirmed: "第2版", book_page: ["p.324"], book_quote: ["不要让有丰厚账面浮盈的未平仓头寸变为亏损！"]
    }
  }
};
