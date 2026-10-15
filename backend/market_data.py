"""Fetch public hourly crypto candles, trying multiple providers in sequence."""
from __future__ import annotations

import requests

BINANCE_URLS = (
    "https://api.binance.com/api/v3/klines",
    "https://api1.binance.com/api/v3/klines",
    "https://api2.binance.com/api/v3/klines",
    "https://api3.binance.com/api/v3/klines",
)
KRAKEN_OHLC_URL = "https://api.kraken.com/0/public/OHLC"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
TIMEOUT_SECONDS = 10


class MarketDataError(RuntimeError):
    pass


def _parse_binance(payload: list) -> list[dict]:
    candles = []
    for row in payload:
        try:
            candles.append({
                "open_time": int(row[0]), "open": float(row[1]),
                "high": float(row[2]), "low": float(row[3]),
                "close": float(row[4]), "volume": float(row[5]),
            })
        except (TypeError, ValueError, IndexError):
            continue
    return candles


def _fetch_kraken(session: requests.Session, symbol: str) -> list[dict]:
    base, quote = symbol[:-4], symbol[-4:]
    if base == "BTC":
        base = "XBT"
    pair = f"{base}{quote}"
    response = session.get(KRAKEN_OHLC_URL, params={"pair": pair, "interval": 60}, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise MarketDataError("; ".join(str(x) for x in payload["error"])[:180])
    result = payload.get("result", {})
    keys = [key for key in result if key != "last"]
    if not keys:
        raise MarketDataError(f"Kraken returned no hourly candles for {pair}.")
    candles = []
    for row in result[keys[0]]:
        try:
            candles.append({
                "open_time": int(row[0]) * 1000, "open": float(row[1]),
                "high": float(row[2]), "low": float(row[3]),
                "close": float(row[4]), "volume": float(row[6]),
            })
        except (TypeError, ValueError, IndexError):
            continue
    return candles


def _fetch_yahoo(session: requests.Session, symbol: str, limit: int) -> list[dict]:
    # Yahoo Finance uses USD tickers such as BTC-USD rather than BTCUSDT.
    base = symbol[:-4]
    ticker = f"{base}-USD"
    response = session.get(
        YAHOO_CHART_URL.format(ticker=ticker),
        params={"range": "1y", "interval": "1h", "events": "history"},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    chart = payload.get("chart", {})
    if chart.get("error"):
        raise MarketDataError(str(chart["error"])[:180])
    results = chart.get("result") or []
    if not results:
        raise MarketDataError(f"Yahoo Finance returned no data for {ticker}.")
    result = results[0]
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    opens, highs, lows = quote.get("open") or [], quote.get("high") or [], quote.get("low") or []
    closes, volumes = quote.get("close") or [], quote.get("volume") or []
    candles = []
    for i, stamp in enumerate(timestamps):
        try:
            if any(values[i] is None for values in (opens, highs, lows, closes)):
                continue
            candles.append({
                "open_time": int(stamp) * 1000, "open": float(opens[i]),
                "high": float(highs[i]), "low": float(lows[i]),
                "close": float(closes[i]), "volume": float(volumes[i] or 0),
            })
        except (TypeError, ValueError, IndexError):
            continue
    return candles[-min(limit, 1000):]


def fetch_hourly_klines(symbol: str, limit: int = 500) -> list[dict]:
    symbol = symbol.strip().upper()
    if not symbol.isalnum() or not 5 <= len(symbol) <= 20 or not symbol.endswith("USDT"):
        raise MarketDataError("Enter a crypto/USDT symbol, for example BTCUSDT or ETHUSDT.")

    limit = max(100, min(int(limit), 1000))
    params = {"symbol": symbol, "interval": "1h", "limit": limit}
    errors = []

    with requests.Session() as session:
        session.headers.update({"User-Agent": "Mozilla/5.0 CryptoPulse/0.2 market research"})
        for url in BINANCE_URLS:
            try:
                response = session.get(url, params=params, timeout=TIMEOUT_SECONDS)
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, list) and payload:
                    candles = _parse_binance(payload)
                    if len(candles) >= 50:
                        return candles
                elif isinstance(payload, dict):
                    errors.append(f"Binance {url.split('/')[2]}: {str(payload.get('msg', 'no candles'))[:100]}")
            except (requests.RequestException, ValueError) as exc:
                errors.append(f"Binance {url.split('/')[2]}: {type(exc).__name__}")

        for provider, fetch in (
            ("Kraken", lambda: _fetch_kraken(session, symbol)),
            ("Yahoo Finance", lambda: _fetch_yahoo(session, symbol, limit)),
        ):
            try:
                candles = fetch()
                if len(candles) >= 50:
                    return candles[-limit:]
                errors.append(f"{provider}: only {len(candles)} valid candles returned")
            except (requests.RequestException, ValueError, MarketDataError) as exc:
                errors.append(f"{provider}: {type(exc).__name__}: {str(exc)[:120]}")

    detail = "; ".join(errors[-6:])
    raise MarketDataError(
        "Could not retrieve enough hourly market data from Binance, Kraken, or Yahoo Finance. "
        "Check your network connection or try again later. "
        f"Details: {detail}"
    )
