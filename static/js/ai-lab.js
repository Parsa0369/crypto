(() => {
 const $=id=>document.getElementById(id), form=$("ai-form"), button=$("ai-run"), status=$("ai-status");
 const fmt=(v,d=2)=>v===null||v===undefined||!Number.isFinite(Number(v))?"—":Number(v).toLocaleString("en-US",{maximumFractionDigits:d});
 function setStatus(m,e=false){status.textContent=m;status.className=e?"status error":"status";}
 function reset(){["ai-direction","ai-price","ai-up","ai-up-label","ai-down-label","ai-accuracy","ai-balanced","ai-brier","ai-samples","ai-feature-count"].forEach(id=>$(id).textContent="—");$("ai-models").replaceChildren();$("ai-features").replaceChildren();$("ai-caveats").replaceChildren();}
 form.addEventListener("submit",async e=>{
  e.preventDefault();const symbol=$("ai-symbol").value.trim().toUpperCase().replace(/[\s/_-]/g,""),horizon=Number($("ai-horizon").value),target=Number($("ai-target").value);
  if(!/^[A-Z0-9]{5,20}USDT$/.test(symbol)){setStatus("نماد معتبر جفت‌ارز USDT وارد کن؛ مثلاً BTCUSDT.",true);return;}
  if(!(target>=1&&target<=100)){setStatus("هدف باید بین ۱ تا ۱۰۰ درصد باشد.",true);return;}
  button.disabled=true;button.textContent="در حال آموزش مدل‌ها…";reset();setStatus("در حال دریافت تاریخچه و آموزش چهار مدل؛ ممکن است کمی طول بکشد…");
  try{
   const response=await fetch("/api/ai-predict",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({symbol,horizon_hours:horizon,target_pct:target}),cache:"no-store"}),data=await response.json();
   if(!response.ok)throw new Error(data.error||"اجرای مدل‌ها ناموفق بود.");
   $("ai-direction").textContent=data.direction;$("ai-price").textContent=symbol+" · آخرین قیمت: "+fmt(data.current_price,8)+" · افق: "+horizon+" ساعت";
   $("ai-up").textContent=fmt(data.probability_up_pct)+"%";$("ai-up-label").textContent=fmt(data.probability_up_pct)+"%";$("ai-down-label").textContent=fmt(data.probability_down_pct)+"%";
   $("ai-ring").style.borderColor=data.probability_up_pct>=58?"#55dfb0":data.probability_up_pct<=42?"#ff7e91":"#8b9cff66";
   $("ai-up-bar").style.width=fmt(data.probability_up_pct)+"%";$("ai-down-bar").style.width=fmt(data.probability_down_pct)+"%";
   $("ai-accuracy").textContent=fmt(data.validation.accuracy_pct)+"%";$("ai-balanced").textContent=fmt(data.validation.balanced_accuracy_pct)+"%";$("ai-brier").textContent=fmt(data.validation.brier_score,4);
   $("ai-samples").textContent=fmt(data.training_samples,0)+" / "+fmt(data.validation.test_samples,0);$("ai-feature-count").textContent="ویژگی‌های ورودی: "+fmt(data.feature_count,0);
   const models=$("ai-models");models.replaceChildren();const head=document.createElement("div");head.className="ai-model-row";
   ["مدل","دقت جهت","Balanced","Brier"].forEach(v=>{const el=document.createElement("span");el.textContent=v;head.appendChild(el);});models.appendChild(head);
   for(const m of data.models||[]){const row=document.createElement("div");row.className="ai-model-row";[m.name,fmt(m.accuracy_pct)+"%",fmt(m.balanced_accuracy_pct)+"%",fmt(m.brier_score,4)].forEach((v,i)=>{const el=document.createElement(i?"strong":"span");el.textContent=v;if(!i)el.className="model-name";row.appendChild(el);});models.appendChild(row);}
   const features=$("ai-features");features.replaceChildren();for(const f of data.top_features||[]){const row=document.createElement("div");row.className="ai-feature-row";const name=document.createElement("span");name.textContent=f.name;const track=document.createElement("div");track.className="ai-feature-track";const fill=document.createElement("span");fill.style.width=Math.min(100,Math.max(0,Number(f.importance_pct)||0))+"%";track.appendChild(fill);const val=document.createElement("strong");val.textContent=fmt(f.importance_pct)+"%";row.append(name,track,val);features.appendChild(row);}
   for(const caveat of data.caveats||[]){const li=document.createElement("li");li.textContent=caveat;$("ai-caveats").appendChild(li);}
   setStatus("آموزش و ارزیابی انجام شد. نتیجه را به‌عنوان برآورد پژوهشی بخوان، نه قطعیت بازار.");
  }catch(err){setStatus(err.message||"خطای نامشخص هنگام آموزش مدل‌ها.",true);}finally{button.disabled=false;button.innerHTML='آموزش و اجرای پیش‌بینی <span>✦</span>';}
 });
})();