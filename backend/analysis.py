"""Transparent historical baseline estimates (not a trained ML model)."""
from statistics import mean, pstdev


def _safe_percent(numerator: int, denominator: int) -> float | None:
    return round(100.0 * numerator / denominator, 2) if denominator else None


def analyze(candles: list[dict], horizon_hours: int, target_pct: float) -> dict:
    if not 1 <= horizon_hours <= 168:
        raise ValueError("For this MVP, choose a horizon between 1 and 168 hours.")
    if not 0 <= target_pct <= 100:
        raise ValueError("Target return must be between 0 and 100 percent.")
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    current = closes[-1]
    if current <= 0:
        raise ValueError("Market data contains an invalid latest price.")

    # Only completed historical windows are included.
    outcomes = []
    for i in range(len(closes) - horizon_hours):
        start = closes[i]
        future_close = closes[i + horizon_hours]
        future_high = max(highs[i + 1:i + horizon_hours + 1])
        future_low = min(lows[i + 1:i + horizon_hours + 1])
        outcomes.append({
            "return_pct": (future_close / start - 1.0) * 100.0,
            "target_hit": future_high >= start * (1.0 + target_pct / 100.0),
            "drawdown_hit": future_low <= start * 0.99,
        })
    if len(outcomes) < 20:
        raise ValueError("Not enough completed historical windows for this horizon.")

    returns = [x["return_pct"] for x in outcomes]
    up = sum(x > 0 for x in returns)
    down = sum(x < 0 for x in returns)
    target_hits = sum(x["target_hit"] for x in outcomes)
    loss_hits = sum(x["return_pct"] < 0 for x in outcomes)
    volatility = pstdev(returns) if len(returns) > 1 else 0.0

    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = changes[-14:]
    gains = sum(max(x, 0.0) for x in recent) / max(1, len(recent))
    losses = sum(max(-x, 0.0) for x in recent) / max(1, len(recent))
    rsi = 100.0 if losses == 0 and gains > 0 else (50.0 if losses == 0 else 100.0 - 100.0 / (1.0 + gains / losses))

    return {
        "price": current, "currency": "USDT", "horizon_hours": horizon_hours, "target_pct": target_pct,
        "sample_count": len(outcomes), "probability_up": _safe_percent(up, len(outcomes)),
        "probability_down": _safe_percent(down, len(outcomes)),
        "probability_target_hit": _safe_percent(target_hits, len(outcomes)),
        "probability_negative_return": _safe_percent(loss_hits, len(outcomes)),
        "mean_return_pct": round(mean(returns), 4), "return_volatility_pct": round(volatility, 4),
        "rsi_14": round(rsi, 2), "method": "Historical frequency baseline",
        "warning": "Descriptive historical frequencies, not calibrated forecasts. They do not guarantee future outcomes.",
    }
