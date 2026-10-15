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
  statusBox.textContent = "در حال دریافت کندل‌ها از منابع جایگزین و محاسبه اندیکاتورها...";
  try {
    const response = await fetch("/api/analyze", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({symbol:$("symbol").value,horizon_hours:horizon,target_pct:Number(target.value)})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "تحلیل انجام نشد.");
    const indicators = data.indicators || {};
    $("price").textContent = fmt(data.price, 6) + " " + (data.currency || "USDT");
    $("asset-label").textContent = data.symbol + " · آخرین کندل ساعتی";
    $("source-label").textContent = "منبع داده: " + (data.source || "سرویس در دسترس");
    $("up-prob").textContent = pct(data.probability_up);
    $("target-prob").textContent = pct(data.probability_target_hit);
    $("down-prob").textContent = pct(data.probability_negative_return);
    $("rsi").textContent = fmt(indicators.rsi_14);
    $("target-caption").textContent = "هدف +" + fmt(data.target_pct) + "% در " + fmt(data.horizon_hours) + " ساعت";
    $("samples").textContent = fmt(data.sample_count, 0);
    $("mean-return").textContent = pct(data.mean_return_pct);
    $("volatility").textContent = pct(data.return_volatility_pct);
    $("method").textContent = data.method;
    $("warning").textContent = data.warning;
    $("ema20").textContent = fmt(indicators.ema_20, 6);
    $("ema50").textContent = fmt(indicators.ema_50, 6);
    $("macd").textContent = fmt(indicators.macd, 6);
    $("macd-signal").textContent = fmt(indicators.macd_signal, 6);
    $("macd-histogram").textContent = fmt(indicators.macd_histogram, 6);
    $("atr").textContent = fmt(indicators.atr_14, 6);
    $("bb-upper").textContent = fmt(indicators.bollinger_upper, 6);
    $("bb-middle").textContent = fmt(indicators.bollinger_middle, 6);
    $("bb-lower").textContent = fmt(indicators.bollinger_lower, 6);
    statusBox.textContent = "تحلیل تمام شد. شاخص‌ها اطلاعات کمکی‌اند و سیگنال قطعی خرید یا فروش نیستند.";
  } catch (error) { showError(error.message || "خطای ناشناخته؛ اتصال اینترنت را بررسی کنید."); }
  finally { button.disabled = false; button.firstChild.textContent = "شروع تحلیل "; }
});
