const form = document.getElementById("analysis-form");
const target = document.getElementById("target");
const targetValue = document.getElementById("target-value");
const button = document.getElementById("analyze-button");
const statusBox = document.getElementById("status");
const $ = (id) => document.getElementById(id);
target.addEventListener("input", () => targetValue.textContent = target.value + "%");
function fmt(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString("en-US", {maximumFractionDigits: digits, minimumFractionDigits: 0});
}
function pct(value) { return value === null || value === undefined ? "—" : fmt(value) + "%"; }
function showError(message) { statusBox.textContent = message; statusBox.className = "status error"; }
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const amount = Number($("amount").value), unit = $("unit").value;
  if (!Number.isInteger(amount) || amount < 1) return showError("مدت باید عدد صحیح مثبت باشد.");
  const horizon = unit === "days" ? amount * 24 : unit === "minutes" ? Math.max(1, Math.ceil(amount / 60)) : amount;
  if (horizon > 168) return showError("در این نسخه، افق زمانی حداکثر ۷ روز است.");
  button.disabled = true;
  button.firstChild.textContent = "در حال دریافت و تحلیل... ";
  statusBox.className = "status";
  statusBox.textContent = "در حال دریافت کندل‌های عمومی بازار و محاسبه نمونه‌های تاریخی...";
  try {
    const response = await fetch("/api/analyze", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({symbol:$("symbol").value,horizon_hours:horizon,target_pct:Number(target.value)})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "تحلیل انجام نشد.");
    $("price").textContent = fmt(data.price, 6) + " USDT";
    $("asset-label").textContent = data.symbol + " · آخرین کندل ساعتی";
    $("up-prob").textContent = pct(data.probability_up);
    $("target-prob").textContent = pct(data.probability_target_hit);
    $("down-prob").textContent = pct(data.probability_negative_return);
    $("rsi").textContent = fmt(data.rsi_14);
    $("target-caption").textContent = "هدف +" + fmt(data.target_pct) + "% در " + fmt(data.horizon_hours) + " ساعت";
    $("samples").textContent = fmt(data.sample_count, 0);
    $("mean-return").textContent = pct(data.mean_return_pct);
    $("volatility").textContent = pct(data.return_volatility_pct);
    $("method").textContent = data.method;
    $("warning").textContent = data.warning;
    statusBox.textContent = "تحلیل تمام شد. این نتیجه فراوانی تاریخی است، نه تضمین آینده.";
  } catch (error) { showError(error.message || "خطای ناشناخته؛ اتصال اینترنت را بررسی کنید."); }
  finally { button.disabled = false; button.firstChild.textContent = "شروع تحلیل "; }
});
