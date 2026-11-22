(function () {
  "use strict";
  const spec = window.ELDER_SPEC;
  const params = spec.params;
  const $ = (id) => document.getElementById(id);
  const state = {symbol:null, marketCode:null, name:"", dailyQfq:[], dailyRaw:[], weeklyQfq:[], minute:[], decision:null, history:[], retry:false, chart:null, series:null, subcharts:[], chartPanes:[], syncingRange:false, syncingCrosshair:false, markers:[], overlay:"ma", track:"qfq"};
  let debounceTimer = null;

  function number(value) { if(value==null||String(value).trim()==="")return null;const n = Number(value); return Number.isFinite(n) ? n : null; }
  function fmt(value, digits=2) { return value == null || !Number.isFinite(value) ? "—" : `¥${value.toFixed(digits)}`; }
  function pct(value) { return value == null || !Number.isFinite(value) ? "—" : `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`; }
  function decodeBars(payload, key) {
    const root = payload && payload.data && payload.data[key];
    if (!root) throw new Error("行情源未返回该股票的数据");
    const field = Object.keys(root).find((item) => /^(qfq)?(day|week)$/.test(item));
    if (!field || !Array.isArray(root[field])) throw new Error("行情数据格式暂不可用");
    // Tencent volume is in lots (手). Convert to shares before indicator calculations.
    return root[field].map((bar) => ({date:String(bar[0]).slice(0,10),open:number(bar[1]),close:number(bar[2]),high:number(bar[3]),low:number(bar[4]),volume:(number(bar[5]) || 0) * 100})).filter((bar) => bar.date && bar.open != null && bar.close != null && bar.high != null && bar.low != null).sort((a,b) => a.date.localeCompare(b.date));
  }
  function decodeMinute(payload, key) {
    const root = payload && payload.data && payload.data[key];
    const values = root && (root.m60 || root.m60v);
    if (!Array.isArray(values)) return [];
    const today = shanghaiDate();
    // Tencent volume is in lots (手). Convert to shares before indicator calculations.
    return values.map((bar) => ({date:normalizeDate(bar[0]),open:number(bar[1]),close:number(bar[2]),high:number(bar[3]),low:number(bar[4]),volume:(number(bar[5]) || 0) * 100})).filter((bar) => bar.date && bar.high != null && !(bar.date === today && !isShanghaiClose())).sort((a,b) => a.date.localeCompare(b.date));
  }
  function normalizeDate(value) {
    const text=String(value);
    if (/^\d{8,12}$/.test(text)) return `${text.slice(0,4)}-${text.slice(4,6)}-${text.slice(6,8)}`;
    return text.slice(0,10);
  }
  function shanghaiDate() { return new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Shanghai",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date()); }
  function isShanghaiClose() {
    const parts = new Intl.DateTimeFormat("en-GB",{timeZone:"Asia/Shanghai",hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).format(new Date()).split(":").map(Number);
    return parts[0] > 15 || (parts[0] === 15 && parts[1] >= 0);
  }
  function closedBars(bars) {
    const today = shanghaiDate();
    const closed = isShanghaiClose();
    return bars.filter((bar) => bar.date < today || (bar.date === today && closed));
  }
  async function fetchJson(url) {
    let last;
    for (let attempt=0;attempt<2;attempt+=1) {
      try {
        const response = await fetch(url,{cache:"no-store"});
        if (!response.ok) throw new Error(`行情服务返回 ${response.status}`);
        const text = await response.text();
        const start = text.indexOf("{");
        if (start < 0) throw new Error("行情服务返回内容无法识别");
        return JSON.parse(text.slice(start));
      } catch (error) { last=error; if (!attempt) await new Promise((resolve) => setTimeout(resolve,600)); }
    }
    throw last || new Error("行情请求失败");
  }
  async function fetchName(code) {
    try {
      const response = await fetch(`https://qt.gtimg.cn/q=${code}`,{cache:"no-store"});
      const bytes = await response.arrayBuffer();
      const text = new TextDecoder("gbk").decode(bytes);
      const fields = text.split('="')[1]?.split("~");
      return fields && fields[1] ? fields[1] : code.toUpperCase();
    } catch (_) { return code.toUpperCase(); }
  }
  async function loadSymbol(input) {
    let parsed;
    try { parsed=ElderEngine.normalizeSymbol(input); }
    catch (error) { setQuerySurface(false); showError(error.message); return; }
    const button=$("query-button"); button.disabled=true;
    setQuerySurface(false);
    setStatus(`${parsed.symbol} 行情加载中…`);
    try {
      const qDayUrl=`https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=${parsed.marketCode},day,,,1000,qfq`;
      const qWeekUrl=`https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=${parsed.marketCode},week,,,300,qfq`;
      const rawUrl=`https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=${parsed.marketCode},day,,,1000,`;
      const minuteUrl=`https://ifzq.gtimg.cn/appstock/app/kline/mkline?param=${parsed.marketCode},m60,,320`;
      const [qd,qw,rd,name,mn]=await Promise.all([
        fetchJson(qDayUrl),fetchJson(qWeekUrl),fetchJson(rawUrl),fetchName(parsed.marketCode),fetchJson(minuteUrl).catch(()=>null)
      ]);
      const dailyQfq=closedBars(decodeBars(qd,parsed.marketCode));
      const weeklyQfq=closedBars(decodeBars(qw,parsed.marketCode));
      const dailyRaw=closedBars(decodeBars(rd,parsed.marketCode));
      if (!dailyQfq.length || !weeklyQfq.length || !dailyRaw.length) throw new Error("没有可用的已收盘日线或周线数据");
      const minute=mn ? decodeMinute(mn,parsed.marketCode) : [];
      const rawByDate=new Map(dailyRaw.map((bar)=>[bar.date,bar]));
      const alignedQfq=dailyQfq.filter((bar)=>rawByDate.has(bar.date));
      if (!alignedQfq.length) throw new Error("前复权与未复权行情日期无法对齐");
      state.symbol=parsed.symbol;state.marketCode=parsed.marketCode;state.name=name;state.isST=/^(\*?ST)/i.test(name);state.dailyQfq=alignedQfq;state.dailyRaw=alignedQfq.map((bar)=>rawByDate.get(bar.date));state.weeklyQfq=weeklyQfq;state.minute=minute;
      state.decision=ElderEngine.decision(state.dailyQfq,state.weeklyQfq,state.dailyRaw,{...params,...spec.market,symbol:state.symbol,market:spec.market,isST:state.isST},state.minute);
      state.history=historicalCheck();
      state.markers=state.history.outcomes.map((row)=>({time:row.date,side:row.side,rule_id:"SYS-05",source_quote:spec.rules["SYS-05"].source_quote,source_url:spec.rules["SYS-05"].source_url,confidence:spec.rules["SYS-05"].confidence,values:row.values,entry:row.entry,stop:row.stop}));
      document.title=`${state.symbol} ${state.name} | 交易决策`;
      $("stock-title").textContent=`${state.symbol} ${state.name}`;
      setQuerySurface(true);
      renderDecision();renderHistory();renderCharts();
      setStatus(`行情截至 ${state.dailyQfq.at(-1).date}，腾讯公开行情接口，非实时。日线 ${state.dailyQfq.length} 根，周线 ${state.weeklyQfq.length} 根${minute.length?`，分钟数据覆盖 ${minute[0].date} 至 ${minute.at(-1).date}`:"，60 分钟接口不可用，触发条件按日线近似"}`);
    } catch (error) { document.title=`${parsed.symbol} 查询失败`;$("stock-title").textContent=`${parsed.symbol} 查询失败`;setQuerySurface(false);showError(`${parsed.symbol} 查询失败：${friendlyError(error)}`); }
    finally { button.disabled=false; }
  }
  function friendlyError(error) {
    const text=String(error && error.message || "");
    if (/Failed to fetch|NetworkError|fetch/i.test(text)) return "网络暂不可用或请求被限流，请稍后重试";
    return text || "行情暂不可用，请稍后重试";
  }
  function setStatus(message) { const line=$("status-line");line.className="status-line";line.textContent=message; }
  function setQuerySurface(visible) { document.querySelectorAll(".decision-shell,.self-check,.charts").forEach((node)=>{node.hidden=!visible;}); }
  function showError(message) {
    const line=$("status-line");line.className="status-line error";line.textContent=message;
    const retry=document.createElement("button");retry.className="retry";retry.textContent="重试";retry.type="button";retry.onclick=()=>loadSymbol($("symbol-input").value);line.append(" ",retry);
  }
  function setupName(direction, vals) {
    if (direction > 0) {
      if (vals.bearPower < 0 && vals.bearPower > vals.previousBear) return "Elder-Ray Bear Power 低于零且回升";
      if (vals.stochK <= params.oversold) return `Stochastic K=${vals.stochK.toFixed(2)} ≤ ${params.oversold}`;
      if (vals.rsi <= params.oversold) return `RSI=${vals.rsi.toFixed(2)} ≤ ${params.oversold}`;
    } else if (direction < 0) {
      if (vals.bullPower > 0 && vals.bullPower < vals.previousBull) return "Elder-Ray Bull Power 高于零且回落";
      if (vals.stochK >= params.overbought) return `Stochastic K=${vals.stochK.toFixed(2)} ≥ ${params.overbought}`;
      if (vals.rsi >= params.overbought) return `RSI=${vals.rsi.toFixed(2)} ≥ ${params.overbought}`;
    }
    return "三项 setup 均不成立";
  }
  function renderDecision() {
    const d=state.decision;
    if (d.insufficient) {
      $("decision-state").className="decision-state state-wait";$("decision-state").innerHTML="<b>WAIT</b><span>观望</span>";
      $("decision-reason").textContent=`数据不足，无法判断（周线 ${d.debug.weekly} 根，日线 ${d.debug.daily} 根）`;
      $("gate-strip").innerHTML="";$("quote-meta").textContent="数据不足";renderRationale(d);return;
    }
    const stateEl=$("decision-state");
    if (d.state === "BUY") {stateEl.className="decision-state state-buy";stateEl.innerHTML="<b>BUY</b><span>买入候选</span>";}
    else if (d.state === "SELL") {stateEl.className="decision-state state-sell";stateEl.innerHTML="<b>SELL</b><span>仅已有持仓</span>";}
    else {stateEl.className="decision-state state-wait";stateEl.innerHTML="<b>WAIT</b><span>观望</span>";}
    $("decision-reason").textContent=d.reason;
    $("quote-meta").textContent=`${d.date} 收盘 ¥${d.close.toFixed(2)} · 涨跌幅 ${pct(d.changePct)} · 板块涨跌幅参考 ${(d.limitPct*100).toFixed(0)}% · ${d.minuteUsed?"60 分钟触发":"日线近似触发"}`;
    const dirPass=d.direction===1;
    const setupLabel=setupName(d.direction,{...d.values,previousBear:d.debug.indicators.bear[d.debug.setupIndex-1],previousBull:d.debug.indicators.bull[d.debug.setupIndex-1]});
    const gates=[
      {name:"第 1 重 · 周线方向",ok:dirPass,text:dirPass?"多头方向已确认":"方向未确认，禁止买入",rule:"SYS-03"},
      {name:"第 2 重 · 日线 setup",ok:d.setup,text:d.setup?setupLabel:"未出现逆势回调 setup",rule:"SYS-04"},
      {name:"第 3 重 · T-1 突破",ok:d.trigger,text:d.trigger?"已触发 / 可评估挂单":d.direction===0?"第一重阻断，未执行触发":`等待 ¥${d.stopEntry.toFixed(2)}`,rule:"SYS-05"}
    ];
    $("gate-strip").innerHTML=gates.map((g)=>`<div class="gate"><span>${g.name} · ${g.rule}</span><strong class="${g.ok?"pass":"fail"}">${escapeHtml(g.text)}</strong></div>`).join("");
    renderRationale(d,setupLabel);
    const entry=d.direction===0?null:d.trigger?d.entryPrice:d.stopEntry, stop=d.stopLoss;
    const target=entry==null||d.direction<0?null:state.dailyRaw.slice(-60).map((r)=>r.high).filter((v)=>v>Math.max(entry,d.close)).sort((a,b)=>a-b)[0]||null;
    $("entry-label").textContent=d.direction<0?"卖出触发参考":"候选入场";
    $("stop-label").textContent=d.direction<0?"平仓保护参考":"保护性止损";
    $("plan-entry").textContent=fmt(entry);$("entry-note").textContent=d.direction===0?"第 1 重未确认，不生成买入价":d.direction<0?"A 股无做空，仅供已有持仓者观察":d.trigger?"触发候选，跳空按开盘价评估":"T-1 raw high + tick";
    $("plan-stop").textContent=fmt(stop);$("stop-note").textContent=stop==null?"方向未确认":d.direction<0?"T-1 raw high + tick，非新仓止损":"T-1 raw low − tick；距入场 ¥"+(entry-stop).toFixed(2);
    $("plan-target").textContent=fmt(target);$("plan-eligibility").textContent=d.state==="SELL"?"SELL 仅用于已有多头持仓平仓，不建立空头":"A 股仅做多 · T+1 · 100 股整手";
    const equity=number($("equity-input").value), used=number($("monthly-used").value)||0;
    const monthOpen=equity==null?null:equity+used;
    const halted=equity!=null && monthOpen>0 && equity<monthOpen*(1-params.monthly_drawdown_limit);
    const allowed=d.state==="BUY" && !d.touchedLimit && equity != null && equity>0 && !halted;
    const plan=equity==null||d.direction!==1||d.state==="SELL"?null:ElderEngine.sizePosition(equity,entry,stop,params,spec.market);
    $("plan-shares").textContent=d.state==="SELL"?"平仓提示":d.direction===0?"方向未确认":d.direction<0?"A 股不做空":plan?`${plan.shares.toLocaleString("zh-CN")} 股`:"请填写权益";
    $("shares-note").textContent=d.state==="SELL"?"仅针对已有持仓；此处不计算新仓":d.direction!==1?"第 1 重方向未允许做多":"风险额 ¥"+(plan? (plan.shares*plan.perShare).toFixed(2):"—")+" · 占权益 "+(equity>0&&entry!=null?(plan.shares*entry/equity*100).toFixed(2):"—")+"%";
    $("risk-math").textContent=equity==null?"请填写账户权益以计算仓位":d.direction!==1?"第 1 重未允许做多，不计算新仓风险预算":`${(params.risk_per_trade*100).toFixed(0)}% 风险预算：¥${(equity*params.risk_per_trade).toFixed(2)} · 每股风险 ¥${(entry-stop).toFixed(2)}`;
    $("monthly-status").textContent=equity==null?"6% 月度风控：填写权益后计算":halted?`6% 月度风控：已触发（回撤 ¥${used.toFixed(2)} / 月初估算 ¥${monthOpen.toFixed(2)}）`:`6% 月度风控：未触发（回撤 ¥${used.toFixed(2)} / 月初估算 ¥${monthOpen.toFixed(2)}）`;
    $("monthly-status").className=halted?"monthly-status halted":"monthly-status";
    $("plan-eligibility").textContent+=halted?" · 本月停止新增仓位":d.state==="BUY"&&!allowed?" · 当前限制下不可新开仓":"";
    $("protect-rule").textContent=`${(params.profit_protect_ratio*100).toFixed(0)}% 浮盈保护：止损参考 = 入场 + ${(params.profit_protect_ratio*100).toFixed(0)}% ×（最高价 − 入场价）`;
    $("cash-warning").textContent=d.state==="SELL"?"":"";
    if(plan&&plan.shares===0&&d.state==="BUY")$("cash-warning").textContent="风险过大或现金不足，不建议开仓";
    const warnings=[];
    if(d.isST)warnings.push("ST 股票不参与")
    if(d.touchedLimit)warnings.push("触及涨停，可能无法成交");
    if(d.state==="SELL")warnings.push("仅针对已有持仓的平仓提示，不做空");
    if(halted)warnings.push("月度 6% 风控已触发，不可新开仓");
    $("trade-warning").textContent=warnings.join("；");
    renderEvidence(gates,setupLabel,plan,entry,stop);
  }
  function renderRationale(d,setupLabel="数据不足，暂不能评估 setup") {
    const host=$("rationale-content");
    if(d.insufficient){host.innerHTML=`<article class="rationale-item"><h3>当前判断</h3><p>${escapeHtml(d.reason)}</p></article><article class="rationale-item"><h3>基本面与消息</h3><p>当前未接入财报、公告或新闻数据，需人工核验后再决策。</p></article>`;return;}
    const directionReason=d.direction===1
      ? `第 1 重通过，周线 EMA 斜率 ${val(d.values.weeklyEmaSlope)}、MACD 柱斜率 ${val(d.values.weeklyHistogramSlope)} 均为正，允许寻找做多机会。`
      : d.direction===-1
        ? `周线方向偏空，EMA 斜率 ${val(d.values.weeklyEmaSlope)}、MACD 柱斜率 ${val(d.values.weeklyHistogramSlope)} 均为负。A 股仅提示已有持仓者管理风险，不做空。`
        : `第 1 重方向未确认，EMA 斜率 ${val(d.values.weeklyEmaSlope)} 与 MACD 柱斜率 ${val(d.values.weeklyHistogramSlope)} 未同向，因此禁止新开多仓。`;
    const setupReason=d.setup?`第 2 重成立：${setupLabel}。`:`第 2 重未成立：${setupLabel}，暂缺少逆势回调条件。`;
    const triggerReason=d.trigger
      ? `第 3 重已触发，参考价 ¥${d.stopEntry.toFixed(2)}，当日高低点为 ¥${d.values.barHighRaw.toFixed(2)} / ¥${d.values.barLowRaw.toFixed(2)}。`
      : d.direction===0
        ? "第 1 重未通过，后续触发不构成买入信号。"
        : `第 3 重尚未触发，等待 T-1 结构价 ¥${d.stopEntry.toFixed(2)}。`;
    const daily=state.dailyRaw,latest=daily.at(-1),lookback=daily.slice(-21),prior=lookback.slice(0,-1);
    const return20=lookback.length>=21&&lookback[0].close?(latest.close/lookback[0].close-1)*100:null;
    const averageVolume=prior.length?prior.reduce((sum,row)=>sum+row.volume,0)/prior.length:null;
    const volumeRatio=averageVolume?latest.volume/averageVolume:null;
    const range= daily.slice(-20),high=range.length?Math.max(...range.map((row)=>row.high)):null,low=range.length?Math.min(...range.map((row)=>row.low)):null;
    const rangePosition=high!=null&&high>low?(latest.close-low)/(high-low)*100:null;
    const marketInfo=`近 20 个交易日涨跌幅 ${pct(return20)}；最新日成交量 ${latest.volume.toLocaleString("zh-CN")} 股${volumeRatio==null?"":`，约为此前 20 日均量的 ${volumeRatio.toFixed(2)} 倍`}；收盘位于 20 日高低区间 ${rangePosition==null?"—":`${rangePosition.toFixed(1)}%`}。`;
    const action=d.state==="BUY"?"买入候选由周线多头、日线 setup 和突破触发共同支持，仍需结合仓位及成交限制执行。":d.state==="SELL"?"出现向下方向信号，仅供已有持仓者评估减仓或平仓，不建立空头。":`当前观望：${d.reason}。`;
    host.innerHTML=`<article class="rationale-item"><h3>判断依据</h3><p>${escapeHtml(action)}</p><p>${escapeHtml(directionReason)}</p><p>${escapeHtml(setupReason)}</p><p>${escapeHtml(triggerReason)}</p></article><article class="rationale-item"><h3>近期市场信息</h3><p>截至 ${escapeHtml(d.date)}，${escapeHtml(marketInfo)}</p></article><article class="rationale-item rationale-caveat"><h3>基本面核验</h3><p>当前行情源未提供经核验的财报、业绩预告、公告或行业消息。本判断不含基本面评价，交易前请核对最新披露信息。</p></article>`;
  }
  function renderEvidence(gates, setupLabel, plan, entry, stop) {
    const d=state.decision, nodes=[];
    const directionValue=`EMA${params.ema_period} 斜率 ${val(d.values.weeklyEmaSlope)}；MACD 柱斜率 ${val(d.values.weeklyHistogramSlope)}；direction=${d.direction}`;
    nodes.push(evidenceNode("第 1 重 · 周线方向","SYS-03",directionValue,spec.rules["SYS-03"]));
    const setupValue=`${setupLabel}；RSI ${val(d.values.rsi)}；K ${val(d.values.stochK)}；Bear ${val(d.values.bearPower)}；Force Index EMA${params.fi_ema} ${val(d.values.force)}（仅参考）`;
    nodes.push(evidenceNode("第 2 重 · 日线 setup","SYS-04",setupValue,spec.rules["SYS-04"]));
    const triggerValue=d.direction===0?`第 1 重 direction=0，SYS-05 跳过；T-1 raw high ${fmt(d.values.previousHighRaw)}，T-1 raw low ${fmt(d.values.previousLowRaw)}`:d.direction>0?`T-1 raw high ${fmt(d.values.previousHighRaw)} + ${params.breakout_offset_ticks} tick = ${fmt(d.stopEntry)}；当日 high ${fmt(d.values.barHighRaw)}`:`T-1 raw low ${fmt(d.values.previousLowRaw)} − ${params.breakout_offset_ticks} tick = ${fmt(d.stopEntry)}；当日 low ${fmt(d.values.barLowRaw)}`;
    nodes.push(evidenceNode("第 3 重 · 突破触发","SYS-05",triggerValue,spec.rules["SYS-05"]));
    const riskValue=plan?`风险预算 ¥${plan.riskBudget.toFixed(2)}；每股风险 ¥${plan.perShare.toFixed(2)}；股数 ${plan.shares}；入场 ${fmt(entry)} / 止损 ${fmt(stop)}`:d.direction===1?"账户权益未填写，未计算仓位":"第 1 重未允许做多，不计算新仓仓位";
    nodes.push(evidenceNode("2% 风险仓位","RISK-01",riskValue,spec.rules["RISK-01"]));
    nodes.push(evidenceNode("6% 月度限制","RISK-02",$("monthly-status").textContent,spec.rules["RISK-02"]));
    const protection=params.profit_protect_ratio;
    nodes.push(evidenceNode(`${(protection*100).toFixed(0)}% 浮盈保护`,"RISK-03",`stop = entry + ${protection.toFixed(2)} × (best_price − entry)`,spec.rules["RISK-03"]));
    $("evidence-chain").innerHTML=nodes.join("");
    $("evidence-summary").textContent=`${d.rules.direction} / ${d.rules.setup} / ${d.rules.trigger}`;
  }
  function evidenceNode(title,id,values,rule) {
    const pages=rule.book_confirmed?`原书第 2 版 ${rule.book_page.join("、")}`:"未确认书内定位";
    const quotes=rule.book_quote?rule.book_quote.map((quote)=>`“${quote}”`).join("；"):"";
    return `<article class="evidence-node"><h3>${escapeHtml(title)} · ${id}</h3><p>${escapeHtml(values)}</p><details><summary>来源与书内确认</summary><p><a href="${escapeAttr(rule.source_url)}" target="_blank" rel="noopener">公开来源</a></p><p>${escapeHtml(rule.source_quote)}</p><p class="book-citation">${escapeHtml(pages)}<br>${escapeHtml(quotes)}</p><p>confidence ${escapeHtml(rule.confidence)}</p></details></article>`;
  }
  function val(x) { return x == null || !Number.isFinite(x) ? "—" : x.toFixed(5); }
  function escapeHtml(s) { return String(s??"").replace(/[&<>"']/g,(c)=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c])); }
  function escapeAttr(s) { return escapeHtml(s); }

  function historicalCheck() {
    const daily=state.dailyQfq,raw=state.dailyRaw,weekly=state.weeklyQfq;
    const dv=ElderEngine.calculate(daily,params),allDirections=ElderEngine.screenOne(weekly,params),dirs=weekly.map((_,i)=>allDirections[i]);
    const outcomes=[];
    const first=Math.max(1,daily.length-250);
    for(let i=first;i<daily.length-5;i+=1){
      const day=daily[i].date;let wi=-1;for(let j=0;j<weekly.length;j+=1)if(weekly[j].date<=day)wi=j;
      const direction=wi>=0?dirs[wi]:0;
      const setupIndex=i-1;
      const setup=ElderEngine.screenTwo(daily,dv,setupIndex,direction,params);
      const previous=raw[i-1], bar=raw[i];
      if(!setup)continue;
      const buy=direction===1 && bar.high>=previous.high+params.breakout_offset_ticks*spec.market.price_tick;
      const sell=direction===-1 && bar.low<=previous.low-params.breakout_offset_ticks*spec.market.price_tick;
      if(!buy&&!sell)continue;
      const exitIndex=i+5;
      const triggerPrice=buy?previous.high+params.breakout_offset_ticks*spec.market.price_tick:previous.low-params.breakout_offset_ticks*spec.market.price_tick;
      const signalEntry=buy?Math.max(raw[i].open,triggerPrice):Math.min(raw[i].open,triggerPrice);
      const signalStop=buy?previous.low-spec.market.price_tick:previous.high+spec.market.price_tick;
      const signalValues={direction,rsi:dv.rsi[setupIndex],force:dv.force[setupIndex],bear:dv.bear[setupIndex],bull:dv.bull[setupIndex],stoch:dv.stoch[setupIndex],previousHigh:previous.high,previousLow:previous.low,triggerPrice,barHigh:bar.high,barLow:bar.low};
      if(buy){const entry=raw[i+1].open,exit=raw[exitIndex].close;outcomes.push({side:"BUY",date:day,ret:(exit/entry-1),entry:signalEntry,stop:signalStop,exit,values:signalValues});}
      else outcomes.push({side:"SELL",date:day,ret:null,entry:signalEntry,stop:signalStop,values:signalValues});
    }
    const trades=outcomes.filter((x)=>x.ret!=null),wins=trades.filter((x)=>x.ret>0);
    let equity=1,peak=1,maxDrawdown=0;
    trades.forEach((trade)=>{equity*=1+trade.ret;peak=Math.max(peak,equity);maxDrawdown=Math.max(maxDrawdown,(peak-equity)/peak);});
    return {outcomes,trades,wins,winRate:trades.length?wins.length/trades.length:null,avg:trades.length?trades.reduce((s,x)=>s+x.ret,0)/trades.length:null,maxDrawdown};
  }
  function renderHistory() {
    const h=state.history, buys=h.outcomes.filter((x)=>x.side==="BUY").length,sells=h.outcomes.filter((x)=>x.side==="SELL").length;
    const metrics=[["规则触发",`${h.outcomes.length} 次`,`${buys} BUY / ${sells} SELL`],["买入样本胜率",pct(h.winRate==null?null:h.winRate*100),`${h.wins.length} / ${h.trades.length} 笔`],["平均收益",pct(h.avg==null?null:h.avg*100),"次日开盘至第 5 日收盘"],["最大回撤",pct(h.maxDrawdown*100),"按样本顺序复利"],["样本范围",`${Math.min(250,state.dailyQfq.length)} 日`,`${state.dailyQfq[Math.max(0,state.dailyQfq.length-250)]?.date||"—"} 至 ${state.dailyQfq.at(-1)?.date||"—"}`]];
    metrics[3][1]=`${(h.maxDrawdown*100).toFixed(2)}%`;
    $("history-metrics").innerHTML=metrics.map(([name,value,note])=>`<div>${name}<strong>${value}</strong>${note}</div>`).join("");
  }

  function formatZhDate(date) { const [y,m,d]=date.split("-").map(Number);return `${y}年${m}月${d}日`; }
  function makeChart(container,height=130,priceFormatter=(price)=>`¥${price.toFixed(2)}`) {
    return LightweightCharts.createChart(container,{height,layout:{background:{color:"#fff"},textColor:"#586366",fontFamily:"-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif",fontSize:11},grid:{vertLines:{color:"#eef0ef"},horzLines:{color:"#eef0ef"}},rightPriceScale:{borderColor:"#d8dfdf"},timeScale:{borderColor:"#d8dfdf",timeVisible:false,tickMarkFormatter:(time,tickMarkType)=>formatChinaTick(time,tickMarkType)},localization:{locale:"zh-CN",timeFormatter:(time)=>`${formatZhDate(chartDate(time))} 北京时间`,priceFormatter},crosshair:{mode:LightweightCharts.CrosshairMode.Normal}});
  }
  function chartDate(time) {
    if(typeof time==="number")return new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Shanghai",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date(time*1000));
    return typeof time==="string"?time:`${time.year}-${String(time.month).padStart(2,"0")}-${String(time.day).padStart(2,"0")}`;
  }
  function formatChinaTick(time,tickMarkType) {
    const [year,month,day]=chartDate(time).split("-").map(Number);
    if(tickMarkType===0)return `${year}年`;
    if(tickMarkType===1)return `${year}年${month}月`;
    return `${month}月${day}日`;
  }
  function registerSynchronizedPane(chart,series,valuesByDate) {
    const pane={chart,series,valuesByDate};
    state.chartPanes.push(pane);
    chart.timeScale().subscribeVisibleLogicalRangeChange((range)=>{
      if(!range||state.syncingRange)return;
      state.syncingRange=true;
      state.chartPanes.forEach((other)=>{if(other!==pane)other.chart.timeScale().setVisibleLogicalRange(range);});
      state.syncingRange=false;
    });
    chart.subscribeCrosshairMove((param)=>{
      if(state.syncingCrosshair)return;
      state.syncingCrosshair=true;
      if(!param.time){
        state.chartPanes.forEach((other)=>{if(other!==pane)other.chart.clearCrosshairPosition();});
      }else{
        const date=chartDate(param.time);
        state.chartPanes.forEach((other)=>{
          if(other===pane)return;
          const value=other.valuesByDate.get(date);
          if(Number.isFinite(value))other.chart.setCrosshairPosition(value,param.time,other.series);
          else other.chart.clearCrosshairPosition();
        });
      }
      state.syncingCrosshair=false;
    });
  }
  function alignPaneRanges() {
    const range=state.chart&&state.chart.timeScale().getVisibleLogicalRange();
    if(!range)return;
    state.syncingRange=true;
    state.chartPanes.forEach((pane)=>{if(pane.chart!==state.chart)pane.chart.timeScale().setVisibleLogicalRange(range);});
    state.syncingRange=false;
  }
  function renderCharts() {
    if(!state.dailyQfq.length)return;
    renderOverlayControls();renderSubchartControls();
    if(state.chart)state.chart.remove();
    state.subcharts.forEach((chart)=>chart.remove());
    state.chartPanes=[];
    const rows=state.track==="raw"?state.dailyRaw:state.dailyQfq;
    const plotRows=withWeekdayGaps(rows);
    const vals=ElderEngine.calculate(rows,params);
    renderOverlayLegend(rows,vals);
    const container=$("price-chart");container.innerHTML="";const tooltipNode=document.createElement("div");tooltipNode.id="chart-tooltip";tooltipNode.className="chart-tooltip";container.append(tooltipNode);
    state.chart=makeChart(container,340);state.series=state.chart.addCandlestickSeries({upColor:"#c73838",downColor:"#167a57",borderUpColor:"#c73838",borderDownColor:"#167a57",wickUpColor:"#c73838",wickDownColor:"#167a57",priceFormat:{type:"price",precision:2,minMove:0.01}});
    state.series.setData(plotRows.map((r)=>r.open==null?{time:r.date}:{time:r.date,open:r.open,high:r.high,low:r.low,close:r.close}));
    registerSynchronizedPane(state.chart,state.series,new Map(rows.map((row)=>[row.date,row.close])));
    const overlay=state.overlay;
    if(overlay==="ma"||overlay==="ema"){
      const periods=overlay==="ma"?state.maPeriods:state.emaPeriods;
      periods.forEach((period,index)=>{const values=overlay==="ma"?simpleMA(rows.map((r)=>r.close),period):ElderEngine.ema(rows.map((r)=>r.close),period);const byDate=new Map(rows.map((r,i)=>[r.date,values[i]]));const line=state.chart.addLineSeries({color:["#315f7a","#947020","#8a5d74","#609176"][index%4],lineWidth:1,priceLineVisible:false,lastValueVisible:true});line.setData(plotRows.map((r)=>{const value=byDate.get(r.date);return value==null?{time:r.date}:{time:r.date,value};}));});
    } else if(overlay==="boll"){
      const period=state.bollPeriod,multiplier=state.bollDeviation,values=boll(rows.map((r)=>r.close),period,multiplier);
      const dateIndex=new Map(rows.map((r,i)=>[r.date,i]));[values.upper,values.middle,values.lower].forEach((line,index)=>{const series=state.chart.addLineSeries({color:["#947020","#315f7a","#947020"][index],lineWidth:1,priceLineVisible:false,lastValueVisible:true,lineStyle:index===1?0:2});series.setData(plotRows.map((r)=>{const i=dateIndex.get(r.date),value=i==null?null:line[i];return value==null?{time:r.date}:{time:r.date,value};}));});
    }
    if($("markers-toggle").checked)state.series.setMarkers(state.markers.filter((m)=>rows.some((r)=>r.date===m.time)).map((m)=>({time:m.time,position:m.side==="BUY"?"belowBar":"aboveBar",color:m.side==="BUY"?"#c73838":"#167a57",shape:m.side==="BUY"?"arrowUp":"arrowDown",text:m.side==="BUY"?"买":"卖"})));
    const tooltip=$("chart-tooltip");
    state.chart.subscribeCrosshairMove((param)=>{if(!param.time||!param.seriesData){tooltip.classList.remove("visible");return;}const bar=param.seriesData.get(state.series);if(!bar){tooltip.classList.remove("visible");return;}const date=chartDate(param.time);tooltip.textContent=`${formatZhDate(date)} 北京时间　开 ¥${bar.open.toFixed(2)}　高 ¥${bar.high.toFixed(2)}　低 ¥${bar.low.toFixed(2)}　收 ¥${bar.close.toFixed(2)}`;tooltip.classList.add("visible");});
    state.chart.subscribeClick((param)=>{if(!param.time)return;const date=typeof param.time==="string"?param.time:`${param.time.year}-${String(param.time.month).padStart(2,"0")}-${String(param.time.day).padStart(2,"0")}`;const marker=state.markers.find((item)=>item.time===date);if(marker){const v=marker.values;showToast(`${marker.side} · ${marker.rule_id} · ${marker.source_quote} · confidence ${marker.confidence} · 入场 ${fmt(marker.entry)} / 止损 ${fmt(marker.stop)} · RSI ${val(v.rsi)} / K ${val(v.stoch)} / Force ${val(v.force)} · ${marker.source_url}`);}});
    $("subcharts").innerHTML="";state.subcharts=[];
    const selected=[...document.querySelectorAll("[data-sub]:checked")].map((e)=>e.dataset.sub);
    selected.forEach((name)=>renderSubchart(name,rows,vals));
    alignPaneRanges();
  }
  state.maPeriods=[5,10,20,60];state.emaPeriods=[13,26];state.bollPeriod=20;state.bollDeviation=2;
  function renderOverlayControls() {
    $("overlay-params").innerHTML="";
    const controls=state.overlay==="ma"?[["MA 周期",state.maPeriods.join(",")]]:state.overlay==="ema"?[["EMA 周期",state.emaPeriods.join(",")]]:state.overlay==="boll"?[["BOLL 周期",String(state.bollPeriod)],["标准差倍数",String(state.bollDeviation)]]:[];
    controls.forEach(([label,value],index)=>{const span=document.createElement("label");span.className="period-control";span.textContent=`${label} `;const input=document.createElement("input");input.value=value;input.setAttribute("aria-label",label);input.addEventListener("change",()=>{const values=input.value.split(",").map(Number).filter((x)=>Number.isInteger(x)&&x>0);if(state.overlay==="ma"&&values.length)state.maPeriods=values;if(state.overlay==="ema"&&values.length)state.emaPeriods=values;if(state.overlay==="boll"&&index===0&&values[0])state.bollPeriod=values[0];if(state.overlay==="boll"&&index===1&&values[0])state.bollDeviation=values[0];renderCharts();});span.append(input);$("overlay-params").append(span);});
  }
  function renderOverlayLegend(rows,values) {
    const host=$("overlay-legend"),last=rows.length-1;
    const entry=(label,value,color)=>`<span class="legend-item"><i class="legend-dot" style="background:${color}"></i>${label} ${value==null?"—":`¥${value.toFixed(2)}`}</span>`;
    if(state.overlay==="boll"){
      const bands=boll(rows.map((row)=>row.close),state.bollPeriod,state.bollDeviation);
      host.innerHTML=[entry(`BOLL 上轨 (${state.bollPeriod},${state.bollDeviation})`,bands.upper[last],"#947020"),entry(`BOLL 中轨 (${state.bollPeriod})`,bands.middle[last],"#315f7a"),entry(`BOLL 下轨 (${state.bollPeriod},${state.bollDeviation})`,bands.lower[last],"#947020")].join("");
      return;
    }
    if(state.overlay==="ema"){
      host.innerHTML=state.emaPeriods.map((period,index)=>entry(`EMA(${period})`,ElderEngine.ema(rows.map((row)=>row.close),period)[last],["#315f7a","#947020","#8a5d74","#609176"][index%4])).join("");
      return;
    }
    if(state.overlay==="ma"){
      host.innerHTML=state.maPeriods.map((period,index)=>entry(`MA(${period})`,simpleMA(rows.map((row)=>row.close),period)[last],["#315f7a","#947020","#8a5d74","#609176"][index%4])).join("");
      return;
    }
    host.innerHTML="";
  }
  function renderSubchartControls() {
    const entries=[["volume","成交量"],["macd","MACD"],["rsi","RSI"],["force","Force Index"],["elder","Elder-Ray"],["stoch","随机指标"]];
    $("subchart-controls").innerHTML=entries.map(([id,label])=>`<label><input type="checkbox" data-sub="${id}" ${id==="volume"||id==="macd"||id==="rsi"?"checked":""}>${label}</label>`).join("");
    document.querySelectorAll("[data-sub]").forEach((input)=>input.addEventListener("change",renderCharts));
  }
  function renderSubchart(name,rows,values) {
    const titles={volume:"成交量（股）",macd:`MACD(${params.macd_fast},${params.macd_slow},${params.macd_signal})`,rsi:`RSI(${params.rsi_period})`,force:`Force Index EMA(${params.fi_ema})`,elder:`Elder-Ray EMA(${params.ema_period})`,stoch:`Stochastic(${params.stoch_k},${params.stoch_d})`};
    const section=document.createElement("section");section.className=`subchart ${name==="volume"?"volume-subchart":""}`;const title=document.createElement("h3");title.textContent=titles[name];const canvas=document.createElement("div");canvas.className="canvas";section.append(title,canvas);$("subcharts").append(section);
    const shareFormatter=(value)=>value>=100000000?`${(value/100000000).toFixed(2)} 亿股`:value>=10000?`${(value/10000).toFixed(2)} 万股`:`${Math.round(value)} 股`;
    const chart=makeChart(canvas,name==="volume"?120:132,name==="volume"?shareFormatter:undefined);state.subcharts.push(chart);const plotRows=withWeekdayGaps(rows),dateIndex=new Map(rows.map((r,i)=>[r.date,i]));
    let crosshairSeries=null,crosshairValues=new Map();
    const add=(data,color,style=0)=>{const line=chart.addLineSeries({color,lineWidth:1,priceLineVisible:false,lastValueVisible:true,lineStyle:style});line.setData(plotRows.map((r)=>{const i=dateIndex.get(r.date),value=i==null?null:data[i];return value==null?{time:r.date}:{time:r.date,value};}));if(!crosshairSeries){crosshairSeries=line;crosshairValues=new Map(rows.map((row,i)=>[row.date,data[i]]));}return line;};
    if(name==="volume"){
      crosshairSeries=chart.addHistogramSeries({priceLineVisible:false,lastValueVisible:true,priceFormat:{type:"custom",minMove:1,formatter:shareFormatter}});
      crosshairValues=new Map(rows.map((row)=>[row.date,row.volume]));
      crosshairSeries.setData(plotRows.map((row)=>{const i=dateIndex.get(row.date);if(i==null)return{time:row.date};const current=rows[i];return{time:row.date,value:current.volume,color:current.close>=current.open?"#c73838":"#167a57"};}));
    }
    if(name==="macd"){add(values.macd,"#315f7a");add(values.macdSignal,"#947020");const hist=chart.addHistogramSeries({priceLineVisible:false,lastValueVisible:true});hist.setData(plotRows.map((r)=>{const i=dateIndex.get(r.date),value=i==null?null:values.histogram[i];return value==null?{time:r.date}:{time:r.date,value,color:value>=0?"#c98181":"#67a78b"};}));}
    if(name==="rsi"){add(values.rsi,"#8a5d74");add(rows.map(()=>params.overbought),"#c6cece",2);add(rows.map(()=>params.oversold),"#c6cece",2);}
    if(name==="force")add(values.force,"#315f7a");
    if(name==="elder"){add(values.bull,"#c73838");add(values.bear,"#167a57");}
    if(name==="stoch"){add(values.stoch,"#315f7a");add(values.stochD,"#947020");add(rows.map(()=>params.overbought),"#c6cece",2);add(rows.map(()=>params.oversold),"#c6cece",2);}
    registerSynchronizedPane(chart,crosshairSeries,crosshairValues);
  }
  function simpleMA(values,period){return values.map((_,i)=>i+1<period?null:values.slice(i+1-period,i+1).reduce((a,b)=>a+b,0)/period);}
  function withWeekdayGaps(rows){const byDate=new Map(rows.map((row)=>[row.date,row]));const result=[];const cursor=new Date(`${rows[0].date}T00:00:00Z`);const end=new Date(`${rows.at(-1).date}T00:00:00Z`);while(cursor<=end){const day=cursor.getUTCDay();const date=cursor.toISOString().slice(0,10);if(day!==0&&day!==6)result.push(byDate.get(date)||{date});cursor.setUTCDate(cursor.getUTCDate()+1);}return result;}
  function boll(values,period,deviation){const middle=simpleMA(values,period),upper=[],lower=[];values.forEach((_,i)=>{if(i+1<period){upper.push(null);lower.push(null);return;}const slice=values.slice(i+1-period,i+1),mean=middle[i],sd=Math.sqrt(slice.reduce((s,v)=>s+(v-mean)**2,0)/period);upper.push(mean+deviation*sd);lower.push(mean-deviation*sd);});return{middle,upper,lower};}
  function bind() {
    $("query-form").addEventListener("submit",(event)=>{event.preventDefault();loadSymbol($("symbol-input").value);});
    $("symbol-input").addEventListener("input",()=>{clearTimeout(debounceTimer);debounceTimer=setTimeout(()=>{if($("symbol-input").value.trim().length>=6)loadSymbol($("symbol-input").value);},550);});
    $("equity-input").addEventListener("input",()=>state.decision&&renderDecision());$("monthly-used").addEventListener("input",()=>state.decision&&renderDecision());
    $("track-select").addEventListener("change",(event)=>{state.track=event.target.value;renderCharts();});
    $("overlay-select").addEventListener("change",(event)=>{state.overlay=event.target.value;renderCharts();});
    $("markers-toggle").addEventListener("change",renderCharts);
  }
  let toastTimer=null;
  function showToast(message){const toast=$("toast");toast.textContent=message;toast.classList.add("show");clearTimeout(toastTimer);toastTimer=setTimeout(()=>toast.classList.remove("show"),3200);}
  window.addEventListener("DOMContentLoaded",()=>{bind();loadSymbol($("symbol-input").value);});
})();
