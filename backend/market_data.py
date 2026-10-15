"""Fetch public historical candles from Binance; no trading credentials needed."""
from __future__ import annotations
import requests

BASE_URL = "https://api.binance.com/api/v3/klines"
TIMEOUT_SECONDS = 8


class MarketDataError(RuntimeError):
    pass


def fetch_hourly_klines(symbol: str, limit: int = 500) -> list[dict]:
    symbol = symbol.strip().upper()
    if not symbol.isalnum() or not 5 <= len(symbol) <= 20:
        raise MarketDataError("Invalid market symbol.")
    params = {"symbol": symbol, "interval": "1h", "limit": max(100, min(int(limit), 1000))}
    try:
        response = requests.get(BASE_URL, params=params, timeout=TIMEOUT_SECONDS,
                                headers={"User-Agent": "CryptoPulse/0.1 local research"})
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise MarketDataError("Could not retrieve market data. Check your connection or try later.") from exc
    if not isinstance(payload, list) or not payload:
        message = payload.get("msg", "Provider returned no candles.") if isinstance(payload, dict) else "Provider returned no candles."
        raise MarketDataError(str(message)[:180])
    candles = []
    for row in payload:
        try:
            candles.append({"open_time": int(row[0]), "open": float(row[1]), "high": float(row[2]),
                            "low": float(row[3]), "close": float(row[4]), "volume": float(row[5])})
        except (TypeError, ValueError, IndexError):
            continue
    if len(candles) < 50:
        raise MarketDataError("Not enough valid historical candles to estimate probabilities.")
    return candles
