"""Transparent historical baseline estimates plus common technical indicators."""
from statistics import mean, pstdev


def _safe_percent(numerator: int, denominator: int) -> float | None:
    return round(100.0 * numerator / denominator, 2) if denominator else None


def _ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1.0 - alpha) * result[-1])
    return result


def _technical_indicators(candles: list[dict]) -> dict:
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    ema20, ema50 = _ema(closes, 20), _ema(closes, 50)
    macd_line = [a - b for a, b in zip(_ema(closes, 12), _ema(closes, 26))]
    macd_signal = _ema(macd_line, 9)
    window = closes[-20:]
    middle = mean(window)
    deviation = pstdev(window)
    true_ranges = []
    for i in range(1, len(candles)):
        true_ranges.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))
    atr14 = mean(true_ranges[-14:]) if true_ranges else 0.0
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = changes[-14:]
    gains = sum(max(x, 0.0) for x in recent) / max(1, len(recent))
    losses = sum(max(-x, 0.0) for x in recent) / max(1, len(recent))
    rsi = 100.0 if losses == 0 and gains > 0 else (
        50.0 if losses == 0 else 100.0 - 100.0 / (1.0 + gains / losses)
    )
    return {
        "rsi_14": round(rsi, 2),
        "ema_20": round(ema20[-1], 8),
        "ema_50": round(ema50[-1], 8),
        "macd": round(macd_line[-1], 8),
        "macd_signal": round(macd_signal[-1], 8),
        "macd_histogram": round(macd_line[-1] - macd_signal[-1], 8),
        "bollinger_upper": round(middle + 2 * deviation, 8),
        "bollinger_middle": round(middle, 8),
        "bollinger_lower": round(middle - 2 * deviation, 8),
        "atr_14": round(atr14, 8),
    }


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

    outcomes = []
    for i in range(len(closes) - horizon_hours):
        start = closes[i]
        future_close = closes[i + horizon_hours]
        future_high = max(highs[i + 1:i + horizon_hours + 1])
        future_low = min(lows[i + 1:i + horizon_hours + 1])
        outcomes.append({
            "return_pct": (future_close / start - 1.0) * 100.0,
            "target_hit": future_high >= start * (1.0 + target_pct / 100.0),
        })
    if len(outcomes) < 20:
        raise ValueError("Not enough completed historical windows for this horizon.")

    returns = [x["return_pct"] for x in outcomes]
    up = sum(x > 0 for x in returns)
    down = sum(x < 0 for x in returns)
    target_hits = sum(x["target_hit"] for x in outcomes)
    loss_hits = sum(x["return_pct"] < 0 for x in outcomes)
    volatility = pstdev(returns) if len(returns) > 1 else 0.0

    return {
        "price": current, "currency": "USDT", "horizon_hours": horizon_hours, "target_pct": target_pct,
        "sample_count": len(outcomes), "probability_up": _safe_percent(up, len(outcomes)),
        "probability_down": _safe_percent(down, len(outcomes)),
        "probability_target_hit": _safe_percent(target_hits, len(outcomes)),
        "probability_negative_return": _safe_percent(loss_hits, len(outcomes)),
        "mean_return_pct": round(mean(returns), 4), "return_volatility_pct": round(volatility, 4),
        "indicators": _technical_indicators(candles),
        "method": "Historical frequency baseline + technical indicators",
        "warning": "Descriptive historical frequencies, not calibrated forecasts. Technical indicators are lagging and do not guarantee future outcomes.",
    }
