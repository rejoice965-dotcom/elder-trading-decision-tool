from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from elder_indicators.config import load_config
from .dashboard import build_payload, calculate_display_indicators


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHART_LIBRARY_URL = (
    "https://unpkg.com/lightweight-charts@4.2.3/"
    "dist/lightweight-charts.standalone.production.js"
)


def _read_indexed_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["timestamp"]).set_index("timestamp").sort_index()


def render_html(payload: dict[str, object]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    serialized = serialized.replace("</", "<\\/")
    document = HTML_TEMPLATE.replace("__CHART_LIBRARY_URL__", CHART_LIBRARY_URL)
    return document.replace("__DASHBOARD_DATA__", serialized)


def build_dashboard(
    *,
    symbol: str,
    name: str,
    cache_dir: Path,
    signals_path: Path,
    output_path: Path,
    config_path: Path,
) -> dict[str, object]:
    config = load_config(config_path)
    code = symbol.replace(".", "_")
    daily_qfq = _read_indexed_csv(cache_dir / f"{code}_daily_qfq.csv")
    daily_raw = _read_indexed_csv(cache_dir / f"{code}_daily_raw.csv")
    signals = pd.read_csv(signals_path)
    if signals.empty:
        raise ValueError(f"No existing signals found in {signals_path}")

    payload = build_payload(
        daily_qfq,
        daily_raw,
        signals,
        params=config["params"],
        market=config["market"],
        symbol=symbol,
    )
    payload["summary"]["name"] = name
    document = render_html(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return {
        "html": str(output_path),
        "symbol": symbol,
        "daily_bars": len(payload["candles"]),
        "signal_markers": len(payload["markers"]),
        "buy_markers": sum(marker["side"] == "BUY" for marker in payload["markers"]),
        "sell_markers": sum(marker["side"] == "SELL" for marker in payload["markers"]),
        "suspension_whitespace_points": len(payload["summary"]["suspension_dates"]),
    }


HTML_TEMPLATE = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>600519.SH 贵州茅台 | 三重滤网研究</title>
<script src="__CHART_LIBRARY_URL__"></script>
<style>
:root{color-scheme:light;--ink:#202a32;--muted:#61707a;--line:#d8dee2;--paper:#fff;--wash:#f5f7f8;--up:#c83b3b;--down:#187b59;--accent:#315f7a;--warn:#8a4a00}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.notice{position:sticky;top:0;z-index:10;padding:8px 18px;background:#26353e;color:#fff;font-weight:600}
main{max-width:1440px;margin:0 auto;padding:0 18px 28px}
.summary{display:flex;align-items:center;gap:22px;flex-wrap:wrap;padding:13px 0 12px;border-bottom:1px solid var(--line)}
.identity{min-width:210px}.identity strong{font-size:20px}.identity span{display:block;color:var(--muted);margin-top:2px}
.metric{min-width:125px}.metric label{display:block;color:var(--muted);font-size:12px}.metric strong{display:block;font-size:16px;font-variant-numeric:tabular-nums;margin-top:3px}
.up{color:var(--up)}.down{color:var(--down)}.neutral{color:var(--muted)}
.badge{display:inline-block;padding:3px 7px;border:1px solid var(--line);border-radius:3px;font-size:12px;margin:2px 5px 2px 0}
.warning{color:var(--warn);border-color:#d7aa70;background:#fff9f0}
.quality{padding:7px 0;color:var(--muted);font-size:12px;border-bottom:1px solid var(--line)}
.section-title{font-size:14px;font-weight:650;margin:12px 0 6px}
#price-chart{height:350px;width:100%;border-bottom:1px solid var(--line)}
.indicator-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 18px}
.indicator-panel{min-width:0;border-bottom:1px solid var(--line);padding:3px 0 8px}
.indicator-title{display:flex;justify-content:space-between;align-items:baseline;font-size:13px;margin:7px 0 3px}
.indicator-title span{color:var(--muted);font-size:12px}
.indicator-chart{height:150px;width:100%}
.detail{border-top:2px solid var(--ink);margin-top:15px;padding:10px 0}
.detail-head{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.detail-head h2{font-size:16px;margin:0 auto 0 0}
.detail-head select{font:inherit;max-width:min(100%,460px);min-height:36px;padding:5px 8px;border:1px solid #89949b;border-radius:3px;background:#fff;color:var(--ink)}
.equity{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:10px 0}
.equity label{font-weight:600}.equity input{width:180px;min-height:36px;padding:5px 8px;border:1px solid #89949b;border-radius:3px;font:inherit;font-variant-numeric:tabular-nums}
.equity-note,.empty{color:var(--muted)}
.provenance{padding:8px 0;border-bottom:1px solid var(--line);font-weight:650}
.detail-grid{display:grid;grid-template-columns:minmax(220px,0.8fr) minmax(300px,1.2fr);gap:20px;padding-top:10px}
.facts{margin:0;display:grid;grid-template-columns:max-content minmax(0,1fr);gap:5px 12px;align-content:start}
.facts dt{color:var(--muted)}.facts dd{margin:0;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
.facts a{color:var(--accent);overflow-wrap:anywhere}
.values-title{font-size:13px;font-weight:650;margin:0 0 5px}
.values{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
.values th,.values td{text-align:left;padding:4px 7px;border-bottom:1px solid #e7ebed;overflow-wrap:anywhere}
.values th{color:var(--muted);font-weight:500}
.small{font-size:12px;color:var(--muted)}
@media(max-width:760px){main{padding:0 12px 20px}.summary{gap:12px}.metric{min-width:calc(50% - 12px)}#price-chart{height:310px}.indicator-grid{grid-template-columns:1fr}.detail-grid{grid-template-columns:1fr}.detail-head select{width:100%;max-width:100%}}
</style>
</head>
<body>
<div class="notice" id="disclaimer"></div>
<main>
  <header class="summary">
    <div class="identity"><strong id="identity"></strong><span id="asof"></span></div>
    <div class="metric"><label>日涨跌幅（未复权）</label><strong id="change"></strong></div>
    <div class="metric"><label>最新收盘（未复权）</label><strong id="last-close"></strong></div>
    <div class="metric"><label>涨跌停参考</label><strong id="limit-summary"></strong></div>
    <div class="metric"><label>交易状态</label><strong id="trading-status"></strong></div>
  </header>
  <div class="quality" id="data-quality"></div>
  <div class="section-title">日线 K 线（前复权）</div>
  <div id="price-chart" aria-label="日线 K 线及买卖信号"></div>
  <div class="indicator-grid">
    <section class="indicator-panel"><div class="indicator-title">MACD <span id="macd-label"></span></div><div id="macd-chart" class="indicator-chart"></div></section>
    <section class="indicator-panel"><div class="indicator-title">Force Index <span id="force-label"></span></div><div id="force-chart" class="indicator-chart"></div></section>
    <section class="indicator-panel"><div class="indicator-title">Elder-Ray <span id="elder-label"></span></div><div id="elder-chart" class="indicator-chart"></div></section>
    <section class="indicator-panel"><div class="indicator-title">RSI <span id="rsi-label"></span></div><div id="rsi-chart" class="indicator-chart"></div></section>
  </div>
  <section class="detail" aria-label="信号详情">
    <div class="detail-head"><h2>信号依据</h2><select id="signal-select" aria-label="选择信号"></select></div>
    <div class="equity">
      <label for="equity-input">账户权益</label>
      <span>¥</span><input id="equity-input" type="number" min="0" step="1000" value="100000" inputmode="decimal">
      <span class="equity-note" id="position-note"></span>
    </div>
    <div class="provenance" id="provenance"></div>
    <div id="signal-warning"></div>
    <div class="detail-grid">
      <dl class="facts" id="facts"></dl>
      <div><div class="values-title">触发时指标与行情值</div><table class="values"><tbody id="indicator-values"></tbody></table></div>
    </div>
  </section>
</main>
<script>
const DATA = __DASHBOARD_DATA__;
const {createChart,CrosshairMode,LineStyle} = LightweightCharts;
const COLORS={red:"#c83b3b",green:"#187b59",ink:"#43515a",amber:"#a36a16",blue:"#315f7a",muted:"#7a858c",grid:"#e7ebed"};
document.getElementById("disclaimer").textContent=DATA.disclaimer;
document.getElementById("provenance").textContent=DATA.provenance;
document.getElementById("identity").textContent=`${DATA.summary.symbol} / ${DATA.summary.name}`;
document.getElementById("asof").textContent=`行情截至 ${DATA.summary.last_date}`;
const change=DATA.summary.change_pct;
const changeEl=document.getElementById("change");
changeEl.textContent=`${change>=0?"+":""}${change.toFixed(2)}%`;
changeEl.className=change>0?"up":(change<0?"down":"neutral");
document.getElementById("last-close").textContent=`¥${DATA.summary.last_raw_close.toFixed(2)}`;
const limit=DATA.summary.limit_status;
document.getElementById("limit-summary").textContent=limit?`¥${limit.lower.toFixed(2)} – ¥${limit.upper.toFixed(2)}`:"待形成前收盘价";
document.getElementById("trading-status").innerHTML=limit&&limit.touched?'<span class="up">触及涨跌停</span>':'<span class="neutral">正常区间</span>';
const boardRate=DATA.config.board_limit_pct[DATA.summary.board];
const stNote=DATA.summary.historical_st_available?"":"历史 ST 状态不可用，按板块阈值参考";
document.getElementById("data-quality").textContent=`指标坐标前复权 qfq · 成交/限价数据未复权 raw · 涨跌停阈值 ${DATA.summary.board} ${(boardRate*100).toFixed(0)}% · ${stNote} · T+1`;
document.getElementById("macd-label").textContent=`EMA(${DATA.config.macd_fast}, ${DATA.config.macd_slow}, ${DATA.config.macd_signal})`;
document.getElementById("force-label").textContent=`EMA(${DATA.config.fi_ema})`;
document.getElementById("elder-label").textContent=`EMA(${DATA.config.ema_period})`;
document.getElementById("rsi-label").textContent=`Wilder ${DATA.config.rsi_period}`;

const baseOptions={
  layout:{background:{color:"#fff"},textColor:COLORS.ink,fontFamily:"-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif",fontSize:12},
  grid:{vertLines:{color:COLORS.grid},horzLines:{color:COLORS.grid}},
  rightPriceScale:{borderColor:COLORS.grid},
  timeScale:{borderColor:COLORS.grid,timeVisible:false,secondsVisible:false,rightOffset:3},
  crosshair:{mode:CrosshairMode.Normal},
  localization:{priceFormatter:value=>`¥${Number(value).toFixed(2)}`},
};
function makeChart(id,height,showTime){
  const node=document.getElementById(id);
  const chart=createChart(node,{...baseOptions,width:node.clientWidth,height, timeScale:{...baseOptions.timeScale,timeVisible:showTime}});
  return chart;
}
const priceChart=makeChart("price-chart",350,false);
const candle=priceChart.addCandlestickSeries({
  upColor:COLORS.red,downColor:COLORS.green,borderUpColor:COLORS.red,borderDownColor:COLORS.green,
  wickUpColor:COLORS.red,wickDownColor:COLORS.green,priceLineVisible:false,
});
candle.setData(DATA.candles);
const line=priceChart.addLineSeries({color:COLORS.blue,lineWidth:2,priceLineVisible:false,lastValueVisible:true,title:`EMA ${DATA.config.ema_period}`});
line.setData(DATA.indicators.filter(row=>row.ema!==null).map(row=>({time:row.time,value:row.ema})));
const markers=DATA.markers.map(item=>({
  time:item.time,
  position:item.side==="BUY"?"belowBar":"aboveBar",
  color:item.side==="BUY"?COLORS.red:COLORS.green,
  shape:item.side==="BUY"?"arrowUp":"arrowDown",
  text:item.marker_label,
  size:1,
}));
candle.setMarkers(markers);

const macdChart=makeChart("macd-chart",150,false);
const histSeries=macdChart.addHistogramSeries({priceLineVisible:false,base:0,lastValueVisible:false});
histSeries.setData(DATA.indicators.filter(row=>row.macd_histogram!==null).map(row=>({time:row.time,value:row.macd_histogram,color:row.macd_histogram>=0?COLORS.red:COLORS.green})));
macdChart.addLineSeries({color:COLORS.blue,lineWidth:1,priceLineVisible:false,lastValueVisible:false}).setData(DATA.indicators.filter(row=>row.macd!==null).map(row=>({time:row.time,value:row.macd})));
macdChart.addLineSeries({color:COLORS.amber,lineWidth:1,priceLineVisible:false,lastValueVisible:false}).setData(DATA.indicators.filter(row=>row.macd_signal!==null).map(row=>({time:row.time,value:row.macd_signal})));

const forceChart=makeChart("force-chart",150,false);
forceChart.addLineSeries({color:COLORS.blue,lineWidth:1.5,priceLineVisible:false}).setData(DATA.indicators.filter(row=>row.force_index!==null).map(row=>({time:row.time,value:row.force_index})));
const elderChart=makeChart("elder-chart",150,false);
elderChart.addLineSeries({color:COLORS.red,lineWidth:1.5,priceLineVisible:false,title:"Bull Power"}).setData(DATA.indicators.filter(row=>row.bull_power!==null).map(row=>({time:row.time,value:row.bull_power})));
elderChart.addLineSeries({color:COLORS.green,lineWidth:1.5,priceLineVisible:false,title:"Bear Power"}).setData(DATA.indicators.filter(row=>row.bear_power!==null).map(row=>({time:row.time,value:row.bear_power})));
const rsiChart=makeChart("rsi-chart",150,false);
rsiChart.addLineSeries({color:COLORS.blue,lineWidth:1.5,priceLineVisible:false}).setData(DATA.indicators.filter(row=>row.rsi!==null).map(row=>({time:row.time,value:row.rsi})));
for(const threshold of [DATA.config.oversold,DATA.config.overbought]){
  rsiChart.addLineSeries({color:COLORS.muted,lineWidth:1,lineStyle:LineStyle.Dashed,priceLineVisible:false,lastValueVisible:false}).setData(DATA.indicators.map(row=>({time:row.time,value:threshold})));
}

const charts=[priceChart,macdChart,forceChart,elderChart,rsiChart];
let syncLock=false;
charts.forEach(chart=>chart.timeScale().subscribeVisibleLogicalRangeChange(range=>{
  if(syncLock||!range)return;
  syncLock=true;
  charts.filter(other=>other!==chart).forEach(other=>other.timeScale().setVisibleLogicalRange(range));
  syncLock=false;
}));
const resizeObserver=new ResizeObserver(()=>charts.forEach(chart=>{
  const parent=chart.chartElement();
  chart.applyOptions({width:parent.clientWidth});
}));
charts.forEach(chart=>resizeObserver.observe(chart.chartElement().parentElement));
priceChart.timeScale().fitContent();

const selector=document.getElementById("signal-select");
const equityInput=document.getElementById("equity-input");
const warning=document.getElementById("signal-warning");
const facts=document.getElementById("facts");
const indicatorValues=document.getElementById("indicator-values");
const positionNote=document.getElementById("position-note");
let activeDaySignals=[];
function money(value){return Number.isFinite(Number(value))?`¥${Number(value).toLocaleString("zh-CN",{minimumFractionDigits:2,maximumFractionDigits:2})}`:"—";}
function fmt(value){if(value===null||value===undefined||!Number.isFinite(Number(value)))return"—";return Number(value).toLocaleString("zh-CN",{maximumFractionDigits:4});}
function esc(value){return String(value).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));}
function showForDate(time){
  const day=typeof time==="string"?time:(time&&time.year?`${time.year}-${String(time.month).padStart(2,"0")}-${String(time.day).padStart(2,"0")}`:"");
  if(!day)return;
  activeDaySignals=DATA.markers.filter(item=>item.time===day);
  selector.replaceChildren();
  if(activeDaySignals.length===0){
    selector.add(new Option(`${day} · 无信号`,""));
    renderSignal(null);
    return;
  }
  activeDaySignals.forEach((item,index)=>selector.add(new Option(`${item.timestamp} · ${item.side} · ${item.rule_id}`,String(index))));
  selector.selectedIndex=0;
  renderSignal(activeDaySignals[0]);
}
function renderSignal(signal){
  if(!signal){
    facts.innerHTML='<dt>日期</dt><dd>当前选择日期没有信号</dd>';
    indicatorValues.innerHTML="";
    warning.innerHTML="";
    positionNote.textContent="";
    return;
  }
  const account=equityInput.value.trim()===""?null:Number(equityInput.value);
  const distance=signal.stop_loss_raw===null?null:Math.abs(signal.price_raw-signal.stop_loss_raw);
  let position={shares:null,risk_budget:null,message:"请输入有效的账户权益以估算仓位。"};
  if(account!==null&&Number.isFinite(account)&&account>0){
    if(signal.side==="SELL"&&!DATA.config.allow_short){
      position={shares:0,risk_budget:account*DATA.config.risk_pct,message:"A 股配置已关闭做空，卖出信号不可作为开空仓位。"};
    }else if(distance===null||distance<=0){
      position={shares:0,risk_budget:account*DATA.config.risk_pct,message:"止损参考价不可用，无法估算仓位。"};
    }else{
      let shares=Math.floor(account*DATA.config.risk_pct/distance);
      shares=Math.floor(shares/DATA.config.minimum_lot)*DATA.config.minimum_lot;
      position={shares,risk_budget:account*DATA.config.risk_pct,message:"按权益风险预算和整手规则估算，不代表实际成交。"};
    }
  }
  positionNote.textContent=position.message;
  facts.innerHTML=[
    ["时间",signal.timestamp],["方向",signal.side],["规则",signal.rule_id],["触发",signal.trigger_rule],
    ["raw 候选价",money(signal.price_raw)],["qfq 图表价",money(signal.price_qfq)],
    ["止损参考价（raw）",signal.stop_loss_raw===null?"—":money(signal.stop_loss_raw)],
    ["单笔风险预算",position.risk_budget===null?"—":money(position.risk_budget)],
    ["估算股数",position.shares===null?"—":`${position.shares.toLocaleString("zh-CN")} 股`],
    ["来源引文",signal.source_quote],["置信度",signal.confidence],
    ["来源 URL",`<a href="${esc(signal.source_url)}" target="_blank" rel="noopener noreferrer">${esc(signal.source_url)}</a>`],
  ].map(([label,value])=>`<dt>${esc(label)}</dt><dd>${value===undefined?"—":(String(value).startsWith("<a ")?value:esc(value))}</dd>`).join("");
  warning.innerHTML=signal.possible_execution_warning
    ?'<div class="badge warning">可能无法成交：信号日触及涨跌停或触发价位本身处于涨跌停</div>'
    :'<div class="badge">信号日未触及配置涨跌停阈值</div>';
  indicatorValues.innerHTML=Object.entries(signal.indicator_values).map(([key,value])=>`<tr><th>${esc(key)}</th><td>${esc(fmt(value))}</td></tr>`).join("");
}
selector.addEventListener("change",()=>renderSignal(activeDaySignals[Number(selector.value)]||null));
equityInput.addEventListener("input",()=>renderSignal(activeDaySignals[Number(selector.value)]||null));
priceChart.subscribeClick(event=>{if(event.time)showForDate(event.time);});
priceChart.subscribeCrosshairMove(event=>{if(event.time)showForDate(event.time);});
const firstSignal=DATA.markers[0];
if(firstSignal)showForDate(firstSignal.time);else renderSignal(null);
</script>
</body>
</html>'''


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the local A-share triple-screen dashboard")
    parser.add_argument("--symbol", default="600519.SH")
    parser.add_argument("--name", default="贵州茅台")
    parser.add_argument("--signals", type=Path, default=PROJECT_ROOT / "examples" / "signals.csv")
    parser.add_argument(
        "--output", type=Path, default=PROJECT_ROOT / "examples" / "triple-screen.html"
    )
    parser.add_argument(
        "--cache-dir", type=Path,
        default=PROJECT_ROOT / "data" / "cache",
    )
    parser.add_argument(
        "--config", type=Path, default=PROJECT_ROOT / "docs" / "indicators.yaml"
    )
    args = parser.parse_args()
    summary = build_dashboard(
        symbol=args.symbol,
        name=args.name,
        cache_dir=args.cache_dir,
        signals_path=args.signals,
        output_path=args.output,
        config_path=args.config,
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
