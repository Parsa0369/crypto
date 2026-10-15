(() => {
  const form = document.getElementById("chart-form");
  const symbolInput = document.getElementById("chart-symbol");
  const intervalInput = document.getElementById("chart-interval");
  const button = document.getElementById("chart-load");
  const status = document.getElementById("chart-status");
  const mount = document.getElementById("tradingview-chart");
  let generation = 0;
  function setStatus(message, error=false) {
    status.textContent = message;
    status.className = error ? "status error" : "status";
  }
  function loadTradingView(event) {
    if (event) event.preventDefault();
    const raw = symbolInput.value.trim().toUpperCase().replace(/[\s/_-]/g, "");
    if (!/^[A-Z0-9]{5,20}$/.test(raw) || !raw.endsWith("USDT")) {
      setStatus("نماد معتبر جفت‌ارز USDT وارد کن؛ مثلاً BTCUSDT.", true);
      symbolInput.focus();
      return;
    }
    const symbol = "BINANCE:" + raw;
    const interval = intervalInput.value;
    const thisGeneration = ++generation;
    button.disabled = true;
    setStatus("در حال بارگذاری نمودار از TradingView…");
    document.getElementById("chart-title").textContent = symbol;
    mount.replaceChildren();
    const container = document.createElement("div");
    container.className = "tradingview-widget-container";
    const widget = document.createElement("div");
    widget.className = "tradingview-widget-container__widget";
    widget.style.width = "100%";
    widget.style.height = "560px";
    const script = document.createElement("script");
    script.type = "text/javascript";
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.async = true;
    const config = {
      autosize: true,
      symbol,
      interval,
      timezone: "Etc/UTC",
      theme: "dark",
      style: "1",
      locale: "en",
      withdateranges: true,
      hide_side_toolbar: false,
      allow_symbol_change: true,
      save_image: false,
      calendar: false,
      support_host: "https://www.tradingview.com"
    };
    script.textContent = JSON.stringify(config);
    container.append(widget, script);
    mount.append(container);
    symbolInput.value = raw;
    window.setTimeout(() => {
      if (thisGeneration !== generation) return;
      setStatus("درخواست نمودار به TradingView ارسال شد. اگر نمایش داده نشد، دسترسی به دامنهٔ TradingView را بررسی کن.");
      button.disabled = false;
    }, 1800);
  }
  form.addEventListener("submit", loadTradingView);
  loadTradingView();
})();