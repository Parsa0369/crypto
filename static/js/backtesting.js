const bt$ = (id) => document.getElementById(id);
const btForm = bt$("backtest-form"), btButton = bt$("bt-run"), btStatus = bt$("bt-status");
function btFmt(v,d=2){return v===null||v===undefined||!Number.isFinite(Number(v))?"—":Number(v).toLocaleString("en-US",{maximumFractionDigits:d})}
function btPct(v){return v===null||v===undefined?"—":btFmt(v)+"%"}
function btStatusSet(msg,error=false){btStatus.textContent=msg;btStatus.className=error?"status error":"status"}
function drawEquity(points){
 const svg=bt$("bt-chart"); svg.replaceChildren();
 if(!Array.isArray(points)||points.length<2){const t=document.createElementNS("http://www.w3.org/2000/svg","text");t.setAttribute("x","360");t.setAttribute("y","110");t.setAttribute("text-anchor","middle");t.textContent="دادهٔ کافی برای رسم نمودار نیست";svg.appendChild(t);return}
 const vals=points.map(p=>Number(p.equity)), min=Math.min(...vals), max=Math.max(...vals), span=max-min||1;
 const coords=vals.map((v,i)=>[(i/(vals.length-1))*690+15,200-((v-min)/span)*175]);
 const line=document.createElementNS("http://www.w3.org/2000/svg","polyline");line.setAttribute("points",coords.map(p=>p.join(",")).join(" "));svg.appendChild(line);
 for(const [x,y] of [[15,20],[15,200],[705,200]]){const tick=document.createElementNS("http://www.w3.org/2000/svg","circle");tick.setAttribute("cx",x);tick.setAttribute("cy",y);tick.setAttribute("r","2");svg.appendChild(tick)}
}
btForm.addEventListener("submit",async e=>{
 e.preventDefault(); const symbol=bt$("bt-symbol").value.trim().toUpperCase().replace(/[\s/_-]/g,""),fee=Number(bt$("bt-fee").value);
 if(!/^[A-Z0-9]{5,20}$/.test(symbol)||!symbol.endsWith("USDT"))return btStatusSet("نماد معتبر USDT وارد کن؛ مثلاً BTCUSDT.",true);
 if(!Number.isFinite(fee)||fee<0||fee>2)return btStatusSet("کارمزد باید بین صفر تا ۲ درصد برای هر سمت باشد.",true);
 btButton.disabled=true;btStatusSet("در حال دریافت کندل‌های تاریخی و اجرای شبیه‌سازی…");
 try{
  const res=await fetch("/api/backtest",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({symbol,fee_pct:fee})});
  const d=await res.json();if(!res.ok)throw new Error(d.error||"بک‌تست انجام نشد.");
  bt$("bt-return").textContent=btPct(d.strategy_return_pct);bt$("bt-benchmark").textContent=btPct(d.buy_and_hold_return_pct);bt$("bt-dd").textContent=btPct(d.max_drawdown_pct);bt$("bt-count").textContent=btFmt(d.trade_count,0);bt$("bt-win").textContent=btPct(d.win_rate_pct);bt$("bt-average").textContent=btPct(d.average_trade_return_pct);
  bt$("bt-meta").textContent=d.symbol+" · "+btFmt(d.candles,0)+" کندل";drawEquity(d.equity_curve);
  bt$("bt-note").textContent=d.note||"نتیجهٔ تاریخی است، نه تضمین آینده.";
  const vb=d.vectorbt_crosscheck||{};
  bt$("bt-vectorbt").textContent=vb.available
    ? "بررسی vectorbt — بازده: "+btPct(vb.total_return_pct)+"؛ بیشترین افت: "+btPct(vb.max_drawdown_pct)+"؛ تعداد معاملات: "+btFmt(vb.trade_count,0)+". "+(vb.note||"")
    : "بررسی متقابل vectorbt فعال نیست؛ "+(vb.reason||"نسخهٔ داخلی بک‌تست استفاده شد.");
  const tbody=bt$("bt-trades");tbody.replaceChildren();
  if(!d.trades||!d.trades.length){const tr=document.createElement("tr"),td=document.createElement("td");td.colSpan=6;td.textContent="در بازهٔ داده‌شده معاملهٔ فرضی ثبت نشد.";tr.appendChild(td);tbody.appendChild(tr)}
  else for(const t of [...d.trades].reverse()){const tr=document.createElement("tr");const values=[t.entry_index,t.exit_index,btFmt(t.entry_price,8),btFmt(t.exit_price,8),btPct(t.return_pct),btFmt(t.duration_hours,0)];values.forEach((v,i)=>{const td=document.createElement("td");td.textContent=v;if(i===4)td.className=Number(t.return_pct)>=0?"positive":"negative";tr.appendChild(td)});tbody.appendChild(tr)}
  btStatusSet("بک‌تست تمام شد. این نتیجه شبیه‌سازی تاریخی است و هیچ سفارشی ارسال نشده است.");
 }catch(err){btStatusSet(err.message||"خطا در اجرای بک‌تست.",true)}finally{btButton.disabled=false}
});