const form = document.getElementById("analysis-form");
const target = document.getElementById("target");
const targetValue = document.getElementById("target-value");
const button = document.getElementById("analyze-button");
const statusBox = document.getElementById("status");
const $ = (id) => document.getElementById(id);
let runnerTimer = null;

function paintRunnerStatus(data) {
  const banner = $("runner-banner");
  const title = $("runner-title");
  const message = $("runner-message");
  const countdown = $("runner-countdown");
  if (runnerTimer) clearInterval(runnerTimer);
  const shutdown = data && data.runner_shutdown_at ? Date.parse(data.runner_shutdown_at) : NaN;
  const generated = data && data.generated_at ? Date.parse(data.generated_at) : NaN;
  if (!Number.isFinite(shutdown)) {
    banner.className = "runner-banner offline";
    title.textContent = "Runner ویندوز هنوز آماده نیست";
    message.textContent = data && data.unavailable
      ? "وضعیت Runner از GitHub دریافت نشد؛ پس از اجرای Workflow اینجا نمایش داده می‌شود."
      : "منتظر اولین اجرای موفق Workflow در GitHub Actions هستیم.";
    countdown.textContent = "--:--:--";
    return;
  }
  const tick = () => {
    const remaining = Math.max(0, shutdown - Date.now());
    const seconds = Math.floor(remaining / 1000);
    const hh = String(Math.floor(seconds / 3600)).padStart(2, "0");
    const mm = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
    const ss = String(seconds % 60).padStart(2, "0");
    countdown.textContent = hh + ":" + mm + ":" + ss;
    if (remaining > 0) {
      banner.className = "runner-banner active";
      title.textContent = "Runner ویندوز فعال است";
      message.textContent = "تا خاموشی خودکار ماشین موقت GitHub Actions زمان باقی مانده است."
        + (Number.isFinite(generated) ? " آخرین به‌روزرسانی داده: " + new Date(generated).toLocaleString() : "");
    } else {
      banner.className = "runner-banner offline";
      title.textContent = "زمان اجرای این Runner تمام شده";
      message.textContent = "داده‌های ذخیره‌شده ممکن است تا اجرای بعدی قابل استفاده باشند؛ اجرای زمان‌بندی‌شده بعدی ممکن است با تأخیر شروع شود.";
    }
  };
  tick();
  runnerTimer = setInterval(tick, 1000);
}

async function refreshRunnerStatus() {
  try {
    const response = await fetch("/api/runner-status", {cache:"no-store"});
    if (!response.ok) throw new Error("Runner status unavailable");
    paintRunnerStatus(await response.json());
  } catch (_) {
    paintRunnerStatus({unavailable:true});
  }
}
refreshRunnerStatus();
setInterval(refreshRunnerStatus, 60000);

target.addEventListener("input", () => targetValue.textContent = target.value + "%");

function normalizeSymbol(value) {
  const compact = String(value || "").toUpperCase().replace(/\s|[\/_-]/g, "");
  if (!compact) return "";
  return compact.endsWith("USDT") ? compact : compact + "USDT";
}
function clearPreviousAnalysis() {
  $("signal-reasons").replaceChildren();
  $("technical-bias").textContent = "در انتظار تحلیل نماد انتخابی";
  $("decision-hint").textContent = "برای دیدن شاخص‌های تازه، دکمهٔ شروع تحلیل را بزن.";
  $("up-prob").textContent = "—";
  $("up-forecast-summary").textContent = "هنوز برای این نماد تحلیلی اجرا نشده است.";
  $("target-prob").textContent = "—";
  $("down-prob").textContent = "—";
  $("technical-score").textContent = "—";
  $("market-regime").textContent = "—";
}
$("symbol").addEventListener("input", clearPreviousAnalysis);
$("symbol").addEventListener("change", clearPreviousAnalysis);

$("symbol").addEventListener("search", clearPreviousAnalysis);

// Populate the search suggestions from the live exchange symbol catalogue.
async function loadSupportedSymbols() {
  const list = $("symbol-options");
  try {
    const response = await fetch("/api/symbols", {cache: "no-store"});
    if (!response.ok) throw new Error("Symbol list unavailable");
    const payload = await response.json();
    const symbols = Array.isArray(payload.symbols) ? payload.symbols : [];
    if (!symbols.length) return;
    list.replaceChildren();
    for (const item of symbols) {
      const option = document.createElement("option");
      option.value = item.symbol;
      option.label = item.base ? item.base + " / USDT" : item.symbol;
      list.appendChild(option);
    }
  } catch (_) {
    // Keep the small built-in list available if the market API is down.
  }
}
loadSupportedSymbols();
function fmt(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString("en-US", {maximumFractionDigits: digits, minimumFractionDigits: 0});
}
function pct(value) { return value === null || value === undefined ? "—" : fmt(value) + "%"; }
function showError(message) { statusBox.textContent = message; statusBox.className = "status error"; }
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const amount = Number($("amount").value), unit = $("unit").value;
  const symbol = normalizeSymbol($("symbol").value);
  if (!symbol || !/^[A-Z0-9]{5,20}$/.test(symbol) || !symbol.endsWith("USDT")) {
    return showError("نماد معتبر وارد کن؛ مثلاً BTC یا BTCUSDT.");
  }
  $("symbol").value = symbol;
  if (!Number.isInteger(amount) || amount < 1) return showError("مدت باید عدد صحیح مثبت باشد.");
  const horizon = unit === "days" ? amount * 24 : unit === "minutes" ? Math.max(1, Math.ceil(amount / 60)) : amount;
  if (horizon > 168) return showError("در این نسخه، افق زمانی حداکثر ۷ روز است.");
  button.disabled = true;
  button.firstChild.textContent = "در حال دریافت و تحلیل... ";
  statusBox.className = "status";
  statusBox.textContent = "در حال دریافت کندل‌ها از منابع جایگزین و محاسبه اندیکاتورها...";
  try {
    const response = await fetch("/api/analyze", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({symbol:symbol,horizon_hours:horizon,target_pct:Number(target.value)})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "تحلیل انجام نشد.");
    const indicators = data.indicators || {};
    $("price").textContent = fmt(data.price, 6) + " " + (data.currency || "USDT");
    $("asset-label").textContent = data.symbol + " · آخرین کندل ساعتی";
    $("source-label").textContent = "منبع داده: " + (data.source || "سرویس در دسترس");
    $("up-prob").textContent = pct(data.probability_up);
    $("up-forecast-summary").textContent =
      "بر اساس " + fmt(data.sample_count, 0) + " بازهٔ تاریخی، فراوانی بازده مثبت در " +
      fmt(data.horizon_hours, 0) + " ساعت: " + pct(data.probability_up) +
      ". این آمار تاریخی است، نه احتمال کالیبره‌شده یا تضمین آینده.";
    $("target-prob").textContent = pct(data.probability_target_hit);
    $("down-prob").textContent = pct(data.probability_negative_return);
    const targetLevels = data.target_frequency_curve || [];
    const highestTarget = data.highest_target_with_50pct_historical_frequency;
    $("target-half-summary").textContent = highestTarget == null ? "هیچ سطحی" : "+" + fmt(highestTarget, 0) + "%";
    $("target-half-label").textContent = highestTarget == null
      ? "فراوانی تاریخی به ۵۰٪ نرسید"
      : "حداقل یک سطح با فراوانی تاریخی ≥ ۵۰٪";
    const curveBox = $("target-curve");
    curveBox.replaceChildren();
    targetLevels.forEach(item => {
      const row = document.createElement("div");
      row.className = "target-curve-row";
      const label = document.createElement("span");
      label.textContent = "+" + fmt(item.target_pct, 0) + "%";
      const track = document.createElement("div");
      track.className = "target-curve-track";
      const fill = document.createElement("div");
      fill.className = "target-curve-fill";
      fill.style.width = Math.max(0, Math.min(100, Number(item.historical_frequency_pct) || 0)) + "%";
      track.appendChild(fill);
      const value = document.createElement("strong");
      value.textContent = pct(item.historical_frequency_pct);
      row.append(label, track, value);
      curveBox.appendChild(row);
    });
    $("technical-bias").textContent = data.technical_bias || "—";
    $("decision-hint").textContent = data.decision_hint || "این برآورد توصیه قطعی خرید یا فروش نیست.";
    $("technical-score").textContent = data.technical_score === undefined ? "—" : fmt(data.technical_score, 0);
    $("market-regime").textContent = data.market_regime || "—";
    const reasonsBox = $("signal-reasons");
    reasonsBox.replaceChildren();
    (data.signal_reasons || []).forEach(item => {
      const row = document.createElement("p");
      row.className = item.effect === "positive" ? "reason-positive" : "reason-negative";
      row.textContent = (item.effect === "positive" ? "＋ " : "− ") + item.reason + " (" + item.points + ")";
      reasonsBox.appendChild(row);
    });
    $("target-zero-note").textContent = data.target_zero_explanation || "";
    $("rsi").textContent = fmt(indicators.rsi_14);
    $("target-caption").textContent = "هدف +" + fmt(data.target_pct) + "% در " + fmt(data.horizon_hours) + " ساعت";
    $("samples").textContent = fmt(data.sample_count, 0);
    $("mean-return").textContent = pct(data.mean_return_pct);
    $("volatility").textContent = pct(data.return_volatility_pct);
    $("method").textContent = data.method;
    $("warning").textContent = data.warning;
    const wf = data.walk_forward_validation || {};
    $("wf-windows").textContent = fmt(wf.test_windows, 0);
    $("wf-status").textContent = wf.status === "ok" ? "تکمیل شد" : "داده ناکافی";
    $("wf-note").textContent = wf.note || "";
    const wfBox = $("wf-models");
    wfBox.replaceChildren();
    (wf.models || []).forEach(model => {
      const row = document.createElement("p");
      row.textContent = model.name + " — MAE: " + fmt(model.mae_pct_points, 4) +
        " واحد درصد؛ دقت جهت: " + fmt(model.directional_accuracy_pct) + "%؛ پنجره‌ها: " +
        fmt(model.test_windows, 0);
      wfBox.appendChild(row);
    });
    $("ema20").textContent = fmt(indicators.ema_20, 6);
    $("ema50").textContent = fmt(indicators.ema_50, 6);
    $("ema200").textContent = fmt(indicators.ema_200, 6);
    $("atr-pct").textContent = pct(indicators.atr_pct);
    $("volume-ratio").textContent = indicators.volume_ratio_20 == null ? "—" : fmt(indicators.volume_ratio_20) + "×";
    $("return-24h").textContent = pct(indicators.return_24h_pct);
    $("return-72h").textContent = pct(indicators.return_72h_pct);
    $("bb-percent-b").textContent = fmt(indicators.bollinger_percent_b, 3);
    $("bb-width").textContent = pct(indicators.bollinger_width_pct);
    $("adx-proxy").textContent = fmt(indicators.adx_proxy_14);
    $("return-p10").textContent = pct(data.historical_return_p10_pct);
    $("return-median").textContent = pct(data.historical_return_median_pct);
    $("return-p90").textContent = pct(data.historical_return_p90_pct);
    $("macd").textContent = fmt(indicators.macd, 6);
    $("macd-signal").textContent = fmt(indicators.macd_signal, 6);
    $("macd-histogram").textContent = fmt(indicators.macd_histogram, 6);
    $("atr").textContent = fmt(indicators.atr_14, 6);
    $("bb-upper").textContent = fmt(indicators.bollinger_upper, 6);
    $("bb-middle").textContent = fmt(indicators.bollinger_middle, 6);
    $("bb-lower").textContent = fmt(indicators.bollinger_lower, 6);
    statusBox.textContent = "تحلیل تمام شد. شاخص‌ها اطلاعات کمکی‌اند و سیگنال قطعی خرید یا فروش نیستند.";
    if (data.runner_shutdown_at) {
      paintRunnerStatus({runner_shutdown_at:data.runner_shutdown_at, generated_at:data.snapshot_generated_at, has_data:true});
    }
  } catch (error) { showError(error.message || "خطای ناشناخته؛ اتصال اینترنت را بررسی کنید."); }
  finally { button.disabled = false; button.firstChild.textContent = "شروع تحلیل "; }
});
