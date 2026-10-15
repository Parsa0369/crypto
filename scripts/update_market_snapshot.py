"""Refresh a public snapshot consumed as a fallback by local CryptoPulse installs."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.market_data import fetch_hourly_klines  # noqa: E402

SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT")


def iso(value: str | None) -> str | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()


def main() -> int:
    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runner_started_at": iso(os.environ.get("RUNNER_STARTED_AT")),
        "runner_shutdown_at": iso(os.environ.get("RUNNER_SHUTDOWN_AT")),
        "refresh_interval_seconds": 900,
        "assets": {},
        "errors": {},
    }
    for symbol in SYMBOLS:
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
    print(f"Wrote {path} with {len(snapshot['assets'])} symbols.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
