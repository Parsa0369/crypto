const $=id=>document.getElementById(id);
const form=$("deep-form"),target=$("deep-target"),targetValue=$("deep-target-value"),startButton=$("deep-start"),resultsBox=$("deep-results");
let pollTimer=null,lastDrawn="";
target.addEventListener("input",()=>targetValue.textContent=target.value+"%");
function fmt(n,d=2){return Number(n).toLocaleString("en-US",{maximumFractionDigits:d});}
function sparkline(points){
 if(!Array.isArray(points)||points.length<2)return '<p class="hint">دادهٔ نمودار کافی نیست.</p>';
 const vals=points.map(p=>p.price),min=Math.min(...vals),max=Math.max(...vals),range=max-min||1;
 const coords=vals.map((v,i)=>(8+i*284/(vals.length-1)).toFixed(1)+","+(68-(v-min)*56/range).toFixed(1)).join(" ");
 return '<svg class="sparkline" viewBox="0 0 300 78" role="img" aria-label="نمودار ۳۶ کندل ساعتی"><polyline points="'+coords+'" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
}
function renderResults(rows){
 const signature=JSON.stringify(rows);if(signature===lastDrawn)return;lastDrawn=signature;resultsBox.replaceChildren();
 if(!rows.length){resultsBox.innerHTML='<div class="panel empty-state">هنوز نتیجه‌ای در دسترس نیست.</div>';return;}
 rows.forEach(row=>{
  const card=document.createElement("article");card.className="panel deep-result-card";
  const heading=document.createElement("div");heading.className="deep-card-heading";
  const name=document.createElement("div"),title=document.createElement("h3");title.textContent=row.symbol;
  const sub=document.createElement("p");sub.className="hint";sub.textContent=row.horizon_hours+" ساعت · هدف +"+fmt(row.target_pct,0)+"%";name.append(title,sub);
  const stat=document.createElement("strong");stat.className="deep-frequency";stat.textContent=fmt(row.historical_frequency_pct)+"%";heading.append(name,stat);
  const bar=document.createElement("div");bar.className="frequency-track";const fill=document.createElement("div");fill.className="frequency-fill";fill.style.width=Math.max(0,Math.min(100,row.historical_frequency_pct))+"%";bar.append(fill);
  const chart=document.createElement("div");chart.className="deep-chart";chart.innerHTML=sparkline(row.chart);
  const footer=document.createElement("div");footer.className="deep-card-footer";
  for(const text of ["آخرین قیمت داده: "+fmt(row.latest_price,8),"نمونه‌ها: "+fmt(row.sample_count,0),row.source||"منبع نامشخص"]){const span=document.createElement("span");span.textContent=text;footer.append(span);}
  card.append(heading,bar,chart,footer);resultsBox.append(card);
 });
}
async function pollStatus(){
 try{
  const response=await fetch("/api/deep-analysis/status",{cache:"no-store"}),state=await response.json();
  $("deep-status-title").textContent=state.status==="running"?"در حال بررسی ارزها…":state.status==="complete"?"اسکن کامل شد":state.status==="error"?"اسکن کامل نشد":"آمادهٔ اسکن";
  $("deep-status-message").textContent=state.status==="running"?"نتایج به‌تدریج اضافه می‌شوند؛ پردازش در پس‌زمینه است.":state.status==="complete"?"اسکن تمام شد. تعداد خطاها: "+(state.errors||[]).length:state.status==="error"?"دادهٔ کافی دریافت نشد؛ اتصال یا Runner را بررسی کن.":"برای شروع درصد هدف را انتخاب کن.";
  $("deep-progress-label").textContent=(state.progress||0)+" / "+(state.total||10);
  $("deep-progress-fill").style.width=(100*(state.progress||0)/Math.max(1,state.total||10))+"%";
  $("deep-engine").textContent=state.engine||"موتور آماده نشده";renderResults(state.results||[]);
  if(state.status!=="running"&&pollTimer){clearInterval(pollTimer);pollTimer=null;startButton.disabled=false;startButton.firstChild.textContent="شروع اسکن ۱۰ ارز ";}
 }catch(_){$("deep-status-message").textContent="ارتباط با سرور برقرار نشد؛ دوباره تلاش می‌شود.";}
}
form.addEventListener("submit",async e=>{
 e.preventDefault();startButton.disabled=true;startButton.firstChild.textContent="در حال شروع… ";
 try{
  const response=await fetch("/api/deep-analysis/start",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({target_pct:Number(target.value)})});
  const data=await response.json();if(!response.ok)throw new Error(data.error||"شروع اسکن ممکن نشد.");
  $("deep-status-message").textContent=data.message||"اسکن شروع شد.";
  if(pollTimer)clearInterval(pollTimer);await pollStatus();pollTimer=setInterval(pollStatus,2500);
 }catch(err){$("deep-status-message").textContent=err.message;startButton.disabled=false;startButton.firstChild.textContent="شروع اسکن ۱۰ ارز ";}
});
pollStatus();