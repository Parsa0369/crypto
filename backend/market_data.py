"""Fetch public historical candles from Binance; no trading credentials needed."""
from __future__ import annotations

import requests

# Try Binance's official API host variants. Network policies may block one hostname.
BASE_URLS = (
    "https://api.binance.com/api/v3/klines",
    "https://api1.binance.com/api/v3/klines",
    "https://api2.binance.com/api/v3/klines",
    "https://api3.binance.com/api/v3/klines",
)
TIMEOUT_SECONDS = 8


class MarketDataError(RuntimeError):
    pass


def fetch_hourly_klines(symbol: str, limit: int = 500) -> list[dict]:
    symbol = symbol.strip().upper()
    if not symbol.isalnum() or not 5 <= len(symbol) <= 20:
        raise MarketDataError("Invalid market symbol.")
    params = {"symbol": symbol, "interval": "1h", "limit": max(100, min(int(limit), 1000))}
    errors = []

    with requests.Session() as session:
        session.headers.update({"User-Agent": "CryptoPulse/0.1 local research"})
        for url in BASE_URLS:
            try:
                response = session.get(url, params=params, timeout=TIMEOUT_SECONDS)
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, list) and payload:
                    break
                if isinstance(payload, dict):
                    message = str(payload.get("msg", "Provider returned no candles."))[:180]
                    errors.append(f"{url.split('/')[2]}: {message}")
                else:
                    errors.append(f"{url.split('/')[2]}: Provider returned no candles.")
            except (requests.RequestException, ValueError) as exc:
                # Keep the user-facing error concise; try the next official hostname.
                errors.append(f"{url.split('/')[2]}: {type(exc).__name__}")
        else:
            detail = "; ".join(errors[-4:])
            raise MarketDataError(
                "Could not retrieve market data from Binance's official API hosts. "
                "Check your internet connection, firewall, or proxy and try again. "
                f"Connection details: {detail}"
            )

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
    if len(candles) < 50:
        raise MarketDataError("Not enough valid historical candles to estimate probabilities.")
    return candles
