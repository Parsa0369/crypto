(() => {
  const $ = id => document.getElementById(id);
  const form = $("chart-form"), button = $("chart-load"), status = $("chart-status");
  const symbolInput = $("chart-symbol");
  function loadTradingViewMarket(){
    const container = $("tv-market-container");
    if (!container || container.dataset.loaded) return;
    container.dataset.loaded = "1";
    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-screener.js";
    script.async = true;
    script.textContent = JSON.stringify({width:"100%",height:490,defaultColumn:"overview",screener_type:"crypto_mkt",displayCurrency:"USD",colorTheme:"dark",locale:"en",isTransparent:true});
    container.appendChild(script);
  }
  loadTradingViewMarket();
  let priceChart, volumeChart, candleSeries, ema20Series, ema50Series, volumeSeries, resizeObserver;
  const fmt = (n, d=4) => n == null || !Number.isFinite(Number(n)) ? "—" : Number(n).toLocaleString("en-US",{maximumFractionDigits:d});
  function setStatus(message, error=false){status.textContent=message;status.className=error?"status error":"status";}
  function ema(data, period){
    const k=2/(period+1), out=[]; let value=null;
    data.forEach((p,i)=>{value=value===null?p.close:p.close*k+value*(1-k);if(i>=period-1)out.push({time:p.time,value});});
    return out;
  }
  function initCharts(){
    if(!window.LightweightCharts){setStatus("کتابخانهٔ نمودار بارگذاری نشد؛ اتصال اینترنت را بررسی کن.",true);return false;}
    const common={layout:{background:{type:LightweightCharts.ColorType.Solid,color:"#0b1220"},textColor:"#aab8cf"},grid:{vertLines:{color:"rgba(139,156,255,.08)"},horzLines:{color:"rgba(139,156,255,.08)"}},rightPriceScale:{borderColor:"#233149"},timeScale:{borderColor:"#233149",timeVisible:true,secondsVisible:false},crosshair:{mode:LightweightCharts.CrosshairMode.Normal}};
    priceChart=LightweightCharts.createChart($("price-chart"),{...common,width:$("price-chart").clientWidth,height:$("price-chart").clientHeight, localization:{locale:"en-US"}});
    candleSeries=priceChart.addSeries(LightweightCharts.CandlestickSeries,{upColor:"#55dfb0",downColor:"#ff7e91",borderUpColor:"#55dfb0",borderDownColor:"#ff7e91",wickUpColor:"#55dfb0",wickDownColor:"#ff7e91"});
    ema20Series=priceChart.addSeries(LightweightCharts.LineSeries,{color:"#8b9cff",lineWidth:2,priceLineVisible:false,lastValueVisible:false});
    ema50Series=priceChart.addSeries(LightweightCharts.LineSeries,{color:"#f5c66c",lineWidth:2,priceLineVisible:false,lastValueVisible:false});
    volumeChart=LightweightCharts.createChart($("volume-chart"),{...common,width:$("volume-chart").clientWidth,height:$("volume-chart").clientHeight,timeScale:{...common.timeScale,visible:true},rightPriceScale:{...common.rightPriceScale,scaleMargins:{top:.1,bottom:0}}});
    volumeSeries=volumeChart.addSeries(LightweightCharts.HistogramSeries,{priceFormat:{type:"volume"},priceScaleId:"right"});
    priceChart.timeScale().subscribeVisibleLogicalRangeChange(range=>{if(range)volumeChart.timeScale().setVisibleLogicalRange(range);});
    volumeChart.timeScale().subscribeVisibleLogicalRangeChange(range=>{if(range)priceChart.timeScale().setVisibleLogicalRange(range);});
    resizeObserver=new ResizeObserver(()=>{priceChart.applyOptions({width:$("price-chart").clientWidth,height:$("price-chart").clientHeight});volumeChart.applyOptions({width:$("volume-chart").clientWidth,height:$("volume-chart").clientHeight});});
    resizeObserver.observe($("price-chart"));resizeObserver.observe($("volume-chart"));
    return true;
  }
  async function loadChart(){
    const symbol=$("chart-symbol").value.trim().toUpperCase().replace(/[\s/_-]/g,""), interval=$("chart-interval").value;
    if(!/^[A-Z0-9]{5,20}$/.test(symbol)||!symbol.endsWith("USDT")){setStatus("نماد معتبر USDT وارد کن؛ مثلاً BTCUSDT.",true);return;}
    if(!priceChart&&!initCharts())return;
    button.disabled=true;setStatus("در حال دریافت داده‌های تاریخی…");
    try{
      const response=await fetch("/api/chart-data?symbol="+encodeURIComponent(symbol)+"&interval="+encodeURIComponent(interval),{cache:"no-store"});
      const data=await response.json();if(!response.ok)throw new Error(data.error||"دادهٔ نمودار دریافت نشد.");
      const rows=data.candles||[];if(rows.length<2)throw new Error("دادهٔ کافی برای نمودار موجود نیست.");
      candleSeries.setData(rows.map(c=>({time:c.time,open:c.open,high:c.high,low:c.low,close:c.close})));
      ema20Series.setData(ema(rows,20));ema50Series.setData(ema(rows,50));
      volumeSeries.setData(rows.map(c=>({time:c.time,value:c.volume,color:c.close>=c.open?"rgba(85,223,176,.48)":"rgba(255,126,145,.48)"})));
      priceChart.timeScale().fitContent();volumeChart.timeScale().fitContent();
      $("chart-title").textContent=symbol+" · کندل‌ها";
      $("chart-source").textContent="منبع داده: "+(data.source||"نامشخص");
      $("chart-last-price").textContent=fmt(rows[rows.length-1].close,8)+" "+(data.currency||"USDT");
      const last=rows[rows.length-1], previous=rows[rows.length-2], change=(last.close/previous.close-1)*100;
      $("chart-change").textContent=(change>0?"+":"")+fmt(change,3)+"%";$("chart-change").style.color=change>=0?"#55dfb0":"#ff7e91";
      $("chart-count").textContent=fmt(rows.length,0);
      $("chart-symbol").value=symbol;setStatus("نمودار با موفقیت بارگذاری شد. داده‌ها ممکن است با تأخیر باشند.");
    }catch(err){setStatus(err.message||"خطا در بارگذاری نمودار.",true);}
    finally{button.disabled=false;}
  }
  form.addEventListener("submit",event=>{event.preventDefault();loadChart();});
  if(window.LightweightCharts)loadChart();else window.addEventListener("load",loadChart,{once:true});
})();