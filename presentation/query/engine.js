(function (root) {
  "use strict";

  function ewm(values, span, minPeriods) {
    const alpha = 2 / (span + 1);
    let state = null;
    let count = 0;
    return values.map((value) => {
      if (value == null || !Number.isFinite(value)) return null;
      state = state == null ? value : alpha * value + (1 - alpha) * state;
      count += 1;
      return count >= minPeriods ? state : null;
    });
  }

  function ema(values, period) { return ewm(values, period, period); }

  function macd(values, cfg) {
    const fast = ema(values, cfg.macd_fast);
    const slow = ema(values, cfg.macd_slow);
    const line = values.map((_, i) => fast[i] == null || slow[i] == null ? null : fast[i] - slow[i]);
    const signal = ewm(line, cfg.macd_signal, cfg.macd_signal);
    return {line, signal, histogram: line.map((value, i) => value == null || signal[i] == null ? null : value - signal[i])};
  }

  function rsi(values, period) {
    const gains = [null];
    const losses = [null];
    for (let i = 1; i < values.length; i += 1) {
      const delta = values[i] - values[i - 1];
      gains.push(Math.max(delta, 0)); losses.push(Math.max(-delta, 0));
    }
    const avgGain = alphaEwm(gains, period);
    const avgLoss = alphaEwm(losses, period);
    return values.map((_, i) => {
      const gain = avgGain[i], loss = avgLoss[i];
      if (gain == null || loss == null) return null;
      if (loss === 0 && gain > 0) return 100;
      if (gain === 0 && loss > 0) return 0;
      if (gain === 0 && loss === 0) return 50;
      return 100 - 100 / (1 + gain / loss);
    });
  }

  function alphaEwm(values, period) {
    const alpha = 1 / period;
    let state = null, count = 0;
    return values.map((value) => {
      if (value == null || !Number.isFinite(value)) return null;
      state = state == null ? value : alpha * value + (1 - alpha) * state;
      count += 1;
      return count >= period ? state : null;
    });
  }

  function calculate(rows, cfg) {
    const close = rows.map((r) => r.close), high = rows.map((r) => r.high), low = rows.map((r) => r.low), volume = rows.map((r) => r.volume);
    const emaLine = ema(close, cfg.ema_period), md = macd(close, cfg);
    const fiRaw = close.map((v, i) => i ? (v - close[i - 1]) * volume[i] : null);
    const force = ewm(fiRaw, cfg.fi_ema, cfg.fi_ema), rs = rsi(close, cfg.rsi_period);
    const bull = high.map((v, i) => emaLine[i] == null ? null : v - emaLine[i]);
    const bear = low.map((v, i) => emaLine[i] == null ? null : v - emaLine[i]);
    const stoch = close.map((v, i) => {
      if (i + 1 < cfg.stoch_k) return null;
      const lo = Math.min(...low.slice(i + 1 - cfg.stoch_k, i + 1));
      const hi = Math.max(...high.slice(i + 1 - cfg.stoch_k, i + 1));
      return hi === lo ? null : (v - lo) * 100 / (hi - lo);
    });
    const stochD = stoch.map((_, i) => {
      const part = stoch.slice(Math.max(0, i + 1 - cfg.stoch_d), i + 1);
      return part.length === cfg.stoch_d && part.every((v) => v != null) ? part.reduce((a, b) => a + b, 0) / part.length : null;
    });
    return {ema: emaLine, macd: md.line, macdSignal: md.signal, histogram: md.histogram, force, rsi: rs, bull, bear, stoch, stochD};
  }

  function directionAt(rows, weeklyValues, index) {
    const prior = index - 1;
    if (prior < 0 || weeklyValues.ema[index] == null || weeklyValues.ema[prior] == null || weeklyValues.histogram[index] == null || weeklyValues.histogram[prior] == null) return 0;
    const emaSlope = weeklyValues.ema[index] - weeklyValues.ema[prior];
    const histSlope = weeklyValues.histogram[index] - weeklyValues.histogram[prior];
    if (emaSlope > 0 && histSlope > 0) return 1;
    if (emaSlope < 0 && histSlope < 0) return -1;
    return 0;
  }

  function screenOne(weeklyRows, cfg) {
    const vals = calculate(weeklyRows, cfg), output = [];
    for (let i = 0; i < weeklyRows.length; i += 1) output.push(directionAt(weeklyRows, vals, i));
    return output;
  }

  function screenTwo(dailyRows, vals, i, direction, cfg) {
    if (i < 1 || direction === 0) return false;
    if (direction > 0) return (Number.isFinite(vals.bear[i]) && vals.bear[i] < 0 && vals.bear[i] > vals.bear[i - 1]) || (Number.isFinite(vals.stoch[i]) && vals.stoch[i] <= cfg.oversold) || (Number.isFinite(vals.rsi[i]) && vals.rsi[i] <= cfg.oversold);
    return (Number.isFinite(vals.bull[i]) && vals.bull[i] > 0 && vals.bull[i] < vals.bull[i - 1]) || (Number.isFinite(vals.stoch[i]) && vals.stoch[i] >= cfg.overbought) || (Number.isFinite(vals.rsi[i]) && vals.rsi[i] >= cfg.overbought);
  }

  function decision(daily, weekly, raw, cfg, minuteRows) {
    const dv = calculate(daily, cfg), wv = calculate(weekly, cfg), dirs = screenOne(weekly, cfg);
    const latest = daily.length - 1, previous = latest - 1;
    if (weekly.length < 35 || daily.length < 60 || previous < 1) return {state:"WAIT", reason:"数据不足，无法判断", insufficient:true, debug:{daily:daily.length,weekly:weekly.length}};
    const date = daily[latest].date;
    let wi = -1;
    for (let i = 0; i < weekly.length; i += 1) if (weekly[i].date <= date) wi = i;
    const direction = dirs[wi] || 0;
    const setup = screenTwo(daily, dv, previous, direction, cfg);
    const previousRaw = raw[previous];
    const buyStop = Number(previousRaw.high) + cfg.breakout_offset_ticks * cfg.price_tick;
    const sellStop = Number(previousRaw.low) - cfg.price_tick;
    const stopLossLong = Number(previousRaw.low) - cfg.price_tick;
    const stopLossShort = Number(previousRaw.high) + cfg.price_tick;
    let minuteUsed = false, crossed = direction > 0 ? Number(raw[latest].high) >= buyStop : Number(raw[latest].low) <= sellStop;
    if (minuteRows && minuteRows.length) {
      const same = minuteRows.filter((r) => r.date === date);
      if (same.length) { minuteUsed = true; crossed = direction > 0 ? same.some((r) => r.high >= buyStop) : same.some((r) => r.low <= sellStop); }
    }
    const isST = Boolean(cfg.isST);
    let state = "WAIT", reason = "", trigger = false;
    if (isST) reason = "ST 股票不参与，当前不建立新仓";
    else if (direction === 0) reason = "第 1 重周线方向未确认，禁止买入";
    else if (!setup) reason = "第 2 重未出现回调 setup，等待";
    else if (!crossed) reason = `第 3 重等待触发价 ¥${(direction > 0 ? buyStop : sellStop).toFixed(2)}`;
    else if (!isST) { state = direction > 0 ? "BUY" : "SELL"; trigger = true; reason = direction > 0 ? "三重滤网通过，触发价已穿越，可评估挂单" : "下行方向触发卖出条件，仅供已有持仓者评估平仓，不做空"; }
    const quote = raw[latest];
    const priorClose = Number(raw[latest - 1].close);
    const changePct = priorClose ? (Number(quote.close) / priorClose - 1) * 100 : 0;
    const board = boardFor(cfg.symbol, cfg.market);
    const limitPct = cfg.market.board_limit_pct[isST ? "st" : board];
    const upper = roundTick(priorClose * (1 + limitPct), cfg.price_tick);
    const lower = roundTick(priorClose * (1 - limitPct), cfg.price_tick);
    const touched = Number(quote.high) >= upper || Number(quote.low) <= lower;
    const stopEntry = direction > 0 ? buyStop : direction < 0 ? sellStop : null;
    const stopLoss = direction > 0 ? stopLossLong : direction < 0 ? stopLossShort : null;
    const entryPrice = direction > 0 ? Math.max(Number(quote.open), buyStop) : direction < 0 ? Math.min(Number(quote.open), sellStop) : null;
    return {state, reason, trigger, date, direction, setup, stopEntry, stopLoss, entryPrice, close:Number(quote.close), changePct, touchedLimit:touched, isST, board, limitPct, minuteUsed, values:{ema13:dv.ema[latest],macd:dv.macd[latest],macdSignal:dv.macdSignal[latest],histogram:dv.histogram[latest],rsi:dv.rsi[previous],force:dv.force[previous],bearPower:dv.bear[previous],bullPower:dv.bull[previous],stochK:dv.stoch[previous],weeklyEmaSlope:wi>0?wv.ema[wi]-wv.ema[wi-1]:null,weeklyHistogramSlope:wi>0?wv.histogram[wi]-wv.histogram[wi-1]:null,previousHighRaw:Number(previousRaw.high),previousLowRaw:Number(previousRaw.low),barHighRaw:Number(quote.high),barLowRaw:Number(quote.low)}, rules:{direction:"SYS-03",setup:"SYS-04",trigger:"SYS-05"}, debug:{dailyIndex:latest,setupIndex:previous,weeklyIndex:wi,dailyBars:daily.length,weeklyBars:weekly.length,indicators:dv,weeklyIndicators:wv,directions:dirs,setupSignal:setup}};
  }

  function roundTick(value, tick) { return Math.floor(value / tick + 0.5) * tick; }
  function boardFor(symbol, market) {
    const code = symbol.split(".")[0];
    for (const [board, prefixes] of Object.entries(market.board_code_prefixes)) if (prefixes.some((p) => code.startsWith(p))) return board;
    return "main_board";
  }
  function normalizeSymbol(value) {
    const input = value.trim().toUpperCase().replace(/\s/g, "");
    const m = input.match(/^(SH|SZ)?(\d{6,9})(\.(SH|SZ))?$/);
    if (!m) throw new Error("代码格式不正确，请输入沪深股票代码");
    const code = m[2];
    let exchange = m[1] || m[4];
    if (!exchange) exchange = /^[569]/.test(code) ? "SH" : "SZ";
    if ((/^(6|9)/.test(code) && exchange !== "SH") || (/^(0|2|3)/.test(code) && exchange !== "SZ")) throw new Error("代码与交易所不匹配，请检查后重试");
    return {symbol:`${code}.${exchange}`, marketCode:`${exchange.toLowerCase()}${code}`};
  }

  function sizePosition(equity, entry, stop, params, market) {
    const perShare = entry - stop;
    if (!(equity > 0 && entry > 0 && perShare > 0)) return {shares:0,riskBudget:Math.max(0,equity)*params.risk_per_trade,perShare};
    const raw = Math.floor(equity * params.risk_per_trade / perShare);
    const affordable = market.cash_only ? Math.min(raw, Math.floor(equity / entry)) : raw;
    return {shares:Math.floor(affordable / market.min_lot) * market.min_lot,riskBudget:equity*params.risk_per_trade,perShare};
  }

  root.ElderEngine = {calculate, decision, normalizeSymbol, sizePosition, boardFor, macd, ema, rsi, screenOne, screenTwo};
})(window);
