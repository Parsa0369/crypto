"""Fetch public hourly candles directly, then use the GitHub Actions snapshot as a fallback."""
from __future__ import annotations

import requests
import time

BINANCE_URLS = (
    "https://api.binance.com/api/v3/klines",
    "https://api1.binance.com/api/v3/klines",
    "https://api2.binance.com/api/v3/klines",
    "https://api3.binance.com/api/v3/klines",
)
KRAKEN_OHLC_URL = "https://api.kraken.com/0/public/OHLC"
BYBIT_KLINE_URL = "https://api.bybit.com/v5/market/kline"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
SNAPSHOT_URL = "https://raw.githubusercontent.com/Parsa0369/crypto/market-data-snapshot/data/market_snapshot.json"
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
                "source": "Binance", "currency": "USDT",
            })
        except (TypeError, ValueError, IndexError):
            continue
    return candles



def _fetch_bybit(session: requests.Session, symbol: str, limit: int) -> list[dict]:
    """Fetch hourly spot candles from Bybit."""
    response = session.get(
        BYBIT_KLINE_URL,
        params={"category": "spot", "symbol": symbol, "interval": "60", "limit": min(limit, 1000)},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("retCode") != 0:
        raise MarketDataError(f"Bybit: {str(payload.get('retMsg', 'request failed'))[:160]}")
    rows = (payload.get("result") or {}).get("list") or []
    candles = []
    for row in rows:
        try:
            candles.append({
                "open_time": int(row[0]), "open": float(row[1]),
                "high": float(row[2]), "low": float(row[3]), "close": float(row[4]),
                "volume": float(row[5]), "source": "Bybit", "currency": "USDT",
            })
        except (TypeError, ValueError, IndexError):
            continue
    return sorted(candles, key=lambda item: item["open_time"])[-limit:]



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
                "high": float(row[2]), "low": float(row[3]), "close": float(row[4]),
                "volume": float(row[6]), "source": "Kraken", "currency": quote,
            })
        except (TypeError, ValueError, IndexError):
            continue
    return candles


def _fetch_yahoo(session: requests.Session, symbol: str, limit: int) -> list[dict]:
    ticker = f"{symbol[:-4]}-USD"
    response = session.get(
        YAHOO_CHART_URL.format(ticker=ticker),
        params={"range": "1y", "interval": "1h", "events": "history"},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    chart = response.json().get("chart", {})
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
                "high": float(highs[i]), "low": float(lows[i]), "close": float(closes[i]),
                "volume": float(volumes[i] or 0), "source": "Yahoo Finance", "currency": "USD",
            })
        except (TypeError, ValueError, IndexError):
            continue
    return candles[-min(limit, 1000):]


def _fetch_actions_snapshot(session: requests.Session, symbol: str, limit: int) -> list[dict]:
    response = session.get(SNAPSHOT_URL, params={"v": "1"}, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    snapshot = response.json()
    assets = snapshot.get("assets", {})
    candles = assets.get(symbol)
    if not isinstance(candles, list) or len(candles) < 50:
        raise MarketDataError(f"GitHub Actions snapshot has no usable data for {symbol}.")
    generated_at = snapshot.get("generated_at")
    shutdown_at = snapshot.get("runner_shutdown_at")
    # Mark the snapshot provenance and carry its update/runner timestamps through the API.
    decorated = []
    for item in candles:
        try:
            candle = {
                "open_time": int(item["open_time"]), "open": float(item["open"]),
                "high": float(item["high"]), "low": float(item["low"]),
                "close": float(item["close"]), "volume": float(item.get("volume", 0)),
                "source": f"GitHub Actions snapshot ({item.get('source', 'market provider')})",
                "currency": item.get("currency", "USD"),
                "snapshot_generated_at": generated_at,
                "runner_shutdown_at": shutdown_at,
            }
            decorated.append(candle)
        except (KeyError, TypeError, ValueError):
            continue
    if len(decorated) < 50:
        raise MarketDataError(f"GitHub Actions snapshot data for {symbol} is invalid.")
    return decorated[-limit:]


def fetch_hourly_klines(symbol: str, limit: int = 500) -> list[dict]:
    symbol = symbol.strip().upper()
    if not symbol.isalnum() or not 5 <= len(symbol) <= 20 or not symbol.endswith("USDT"):
        raise MarketDataError("Enter a crypto/USDT symbol, for example BTCUSDT or ETHUSDT.")

    limit = max(100, min(int(limit), 1000))
    params = {"symbol": symbol, "interval": "1h", "limit": limit}
    errors = []

    with requests.Session() as session:
        session.headers.update({"User-Agent": "Mozilla/5.0 CryptoPulse/0.3 market research"})
        for url in BINANCE_URLS:
            try:
                response = session.get(url, params=params, timeout=TIMEOUT_SECONDS)
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, list) and payload:
                    candles = _parse_binance(payload)
                    if len(candles) >= 50:
                        return candles[-limit:]
                elif isinstance(payload, dict):
                    errors.append(f"Binance {url.split('/')[2]}: {str(payload.get('msg', 'no candles'))[:100]}")
            except (requests.RequestException, ValueError) as exc:
                errors.append(f"Binance {url.split('/')[2]}: {type(exc).__name__}")

        for provider, fetch in (
            ("Bybit", lambda: _fetch_bybit(session, symbol, limit)),
            ("Kraken", lambda: _fetch_kraken(session, symbol)),
            ("Yahoo Finance", lambda: _fetch_yahoo(session, symbol, limit)),
            ("GitHub Actions snapshot", lambda: _fetch_actions_snapshot(session, symbol, limit)),
        ):
            try:
                candles = fetch()
                if len(candles) >= 50:
                    return candles[-limit:]
                errors.append(f"{provider}: only {len(candles)} valid candles returned")
            except (requests.RequestException, ValueError, MarketDataError) as exc:
                errors.append(f"{provider}: {type(exc).__name__}: {str(exc)[:120]}")

    detail = "; ".join(errors[-7:])
    raise MarketDataError(
        "Could not retrieve enough hourly market data from Binance, Kraken, Yahoo Finance, or the GitHub Actions snapshot. "
        "The scheduled runner must have completed at least one successful refresh. "
        f"Details: {detail}"
    )


def get_runner_status() -> dict:
    """Read the public snapshot metadata for the dashboard countdown."""
    try:
        response = requests.get(SNAPSHOT_URL, params={"status": str(int(time.time() // 60))}, timeout=6,
                                headers={"User-Agent": "CryptoPulse/0.3"})
        response.raise_for_status()
        snapshot = response.json()
        return {
            "generated_at": snapshot.get("generated_at"),
            "runner_started_at": snapshot.get("runner_started_at"),
            "runner_shutdown_at": snapshot.get("runner_shutdown_at"),
            "refresh_interval_seconds": snapshot.get("refresh_interval_seconds", 900),
            "has_data": bool(snapshot.get("assets")),
        }
    except (requests.RequestException, ValueError):
        return {"generated_at": None, "runner_started_at": None,
                "runner_shutdown_at": None, "refresh_interval_seconds": 900,
                "has_data": False, "unavailable": True}


def get_supported_symbols() -> list[dict]:
    """Read exchange symbols discovered by the scheduled runner; do not query exchanges here."""
    try:
        response = requests.get(SNAPSHOT_URL, params={"symbols": "1"}, timeout=6,
                                headers={"User-Agent": "CryptoPulse/0.3"})
        response.raise_for_status()
        snapshot = response.json()
        symbols = snapshot.get("symbols", [])
        if isinstance(symbols, list) and symbols:
            valid = [
                {"symbol": item["symbol"], "base": item.get("base", ""),
                 "exchange": item.get("exchange", "market runner")}
                for item in symbols
                if isinstance(item, dict) and isinstance(item.get("symbol"), str)
                and item["symbol"].isalnum() and item["symbol"].endswith("USDT")
            ]
            if valid:
                return sorted(valid, key=lambda item: item["symbol"])
    except (requests.RequestException, ValueError, TypeError):
        pass
    # Fallback list is used only until the scheduled runner publishes its first symbol list.
    return [{"symbol": symbol, "base": symbol[:-4], "exchange": "fallback"} for symbol in
            ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
             "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT")]
