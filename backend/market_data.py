"""Fetch public hourly crypto candles from Binance, then Kraken as a fallback."""
from __future__ import annotations

import requests

BINANCE_URLS = (
    "https://api.binance.com/api/v3/klines",
    "https://api1.binance.com/api/v3/klines",
    "https://api2.binance.com/api/v3/klines",
    "https://api3.binance.com/api/v3/klines",
)
KRAKEN_OHLC_URL = "https://api.kraken.com/0/public/OHLC"
TIMEOUT_SECONDS = 10


class MarketDataError(RuntimeError):
    pass


def _parse_binance(payload: list) -> list[dict]:
    candles = []
    for row in payload:
        try:
            candles.append({
                "open_time": int(row[0]),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            })
        except (TypeError, ValueError, IndexError):
            continue
    return candles


def _fetch_kraken(session: requests.Session, symbol: str) -> list[dict]:
    # Kraken uses XBT instead of BTC for Bitcoin in pair names.
    base = symbol[:-4]
    quote = symbol[-4:]
    if base == "BTC":
        base = "XBT"
    pair = f"{base}{quote}"
    response = session.get(
        KRAKEN_OHLC_URL,
        params={"pair": pair, "interval": 60},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise MarketDataError("; ".join(str(x) for x in payload["error"])[:180])
    result = payload.get("result", {})
    pair_keys = [key for key in result if key != "last"]
    if not pair_keys:
        raise MarketDataError(f"Kraken returned no hourly candles for {pair}.")
    candles = []
    for row in result[pair_keys[0]]:
        try:
            candles.append({
                "open_time": int(row[0]) * 1000,
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[6]),
            })
        except (TypeError, ValueError, IndexError):
            continue
    return candles


def fetch_hourly_klines(symbol: str, limit: int = 500) -> list[dict]:
    symbol = symbol.strip().upper()
    if not symbol.isalnum() or not 5 <= len(symbol) <= 20 or not symbol.endswith("USDT"):
        raise MarketDataError("Enter a crypto/USDT symbol, for example BTCUSDT or ETHUSDT.")

    limit = max(100, min(int(limit), 1000))
    params = {"symbol": symbol, "interval": "1h", "limit": min(limit, 1000)}
    errors = []

    with requests.Session() as session:
        session.headers.update({"User-Agent": "CryptoPulse/0.1 local research"})
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

        try:
            candles = _fetch_kraken(session, symbol)
            if len(candles) >= 50:
                # Kraken returns up to 720 recent hourly candles.
                return candles[-min(limit, 720):]
            errors.append(f"Kraken: only {len(candles)} valid candles returned")
        except (requests.RequestException, ValueError, MarketDataError) as exc:
            errors.append(f"Kraken: {type(exc).__name__}: {str(exc)[:120]}")

    detail = "; ".join(errors[-5:])
    raise MarketDataError(
        "Could not retrieve enough hourly market data from Binance or Kraken. "
        "Check your network connection or try a supported USDT pair. "
        f"Details: {detail}"
    )
