"""Discover spot USDT pairs on the scheduled runner and refresh liquid hourly candles."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.market_data import fetch_hourly_klines  # noqa: E402

BINANCE_INFO = "https://api.binance.com/api/v3/exchangeInfo"
BINANCE_TICKERS = "https://api.binance.com/api/v3/ticker/24hr"
BYBIT_INSTRUMENTS = "https://api.bybit.com/v5/market/instruments-info"
BYBIT_TICKERS = "https://api.bybit.com/v5/market/tickers"
MAX_CANDLE_SYMBOLS = 40
FALLBACK_SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
                    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT")


def iso(value: str | None) -> str | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()


def discover_symbols() -> tuple[list[dict], list[str]]:
    """Query exchanges from the runner, merge active USDT spot pairs, rank by reported turnover."""
    session = requests.Session()
    session.headers.update({"User-Agent": "CryptoPulse/0.4 market runner"})
    symbols: dict[str, dict] = {}
    volume: dict[str, float] = {}

    try:
        response = session.get(BINANCE_INFO, timeout=15)
        response.raise_for_status()
        for item in response.json().get("symbols", []):
            if (item.get("status") == "TRADING" and item.get("quoteAsset") == "USDT"
                    and item.get("isSpotTradingAllowed", True)):
                symbol = item.get("symbol", "")
                if symbol.isalnum():
                    symbols[symbol] = {"symbol": symbol, "base": item.get("baseAsset", ""),
                                       "exchange": "Binance"}
        response = session.get(BINANCE_TICKERS, timeout=20)
        response.raise_for_status()
        for item in response.json():
            symbol = item.get("symbol", "")
            if symbol in symbols:
                try:
                    volume[symbol] = float(item.get("quoteVolume", 0))
                except (TypeError, ValueError):
                    pass
    except (requests.RequestException, ValueError, TypeError) as exc:
        print(f"Binance symbol discovery warning: {type(exc).__name__}: {exc}")

    try:
        response = session.get(BYBIT_INSTRUMENTS,
                               params={"category": "spot", "limit": 1000}, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if payload.get("retCode") == 0:
            for item in (payload.get("result") or {}).get("list", []):
                if item.get("status") == "Trading" and item.get("quoteCoin") == "USDT":
                    symbol = item.get("symbol", "")
                    if symbol.isalnum():
                        symbols.setdefault(symbol, {"symbol": symbol, "base": item.get("baseCoin", ""),
                                                    "exchange": "Bybit"})
        response = session.get(BYBIT_TICKERS, params={"category": "spot"}, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if payload.get("retCode") == 0:
            for item in (payload.get("result") or {}).get("list", []):
                symbol = item.get("symbol", "")
                if symbol in symbols:
                    try:
                        volume[symbol] = max(volume.get(symbol, 0), float(item.get("turnover24h", 0)))
                    except (TypeError, ValueError):
                        pass
    except (requests.RequestException, ValueError, TypeError) as exc:
        print(f"Bybit symbol discovery warning: {type(exc).__name__}: {exc}")

    if not symbols:
        symbols = {symbol: {"symbol": symbol, "base": symbol[:-4], "exchange": "fallback"}
                   for symbol in FALLBACK_SYMBOLS}
    symbol_list = sorted(symbols.values(), key=lambda item: item["symbol"])
    ranked = sorted(symbols, key=lambda symbol: volume.get(symbol, 0), reverse=True)
    if not any(volume.values()):
        ranked = [item["symbol"] for item in symbol_list]
    return symbol_list, ranked[:MAX_CANDLE_SYMBOLS]


def main() -> int:
    symbols, candle_symbols = discover_symbols()
    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runner_started_at": iso(os.environ.get("RUNNER_STARTED_AT")),
        "runner_shutdown_at": iso(os.environ.get("RUNNER_SHUTDOWN_AT")),
        "refresh_interval_seconds": 900,
        "symbols": symbols,
        "assets": {},
        "errors": {},
    }
    print(f"Runner discovered {len(symbols)} active USDT spot pairs; refreshing {len(candle_symbols)} candle histories.")
    for symbol in candle_symbols:
        try:
            candles = fetch_hourly_klines(symbol, limit=500)
            snapshot["assets"][symbol] = candles
            print(f"{symbol}: saved {len(candles)} candles from {candles[-1].get('source', 'unknown')}")
        except Exception as exc:
            snapshot["errors"][symbol] = f"{type(exc).__name__}: {str(exc)[:180]}"
            print(f"{symbol}: unavailable ({snapshot['errors'][symbol]})")

    if not snapshot["assets"]:
        print("No symbols could be refreshed; keeping the previous snapshot if one exists.", file=sys.stderr)
        return 1

    path = ROOT / "data" / "market_snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {path}: {len(symbols)} searchable pairs, {len(snapshot['assets'])} histories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
