"""Transparent historical baseline and multi-factor technical analysis.

Indicators describe recent market conditions; they are not calibrated forecasts.
"""
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


def _rsi(closes: list[float], period: int = 14) -> float:
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = changes[-period:]
    if not recent:
        return 50.0
    gains = sum(max(x, 0.0) for x in recent) / len(recent)
    losses = sum(max(-x, 0.0) for x in recent) / len(recent)
    if losses == 0:
        return 100.0 if gains > 0 else 50.0
    return 100.0 - 100.0 / (1.0 + gains / losses)


def _technical_indicators(candles: list[dict]) -> dict:
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    volumes = [max(0.0, float(c.get("volume", 0) or 0)) for c in candles]
    ema20, ema50 = _ema(closes, 20), _ema(closes, 50)
    ema200 = _ema(closes, 200)
    macd_line = [a - b for a, b in zip(_ema(closes, 12), _ema(closes, 26))]
    macd_signal = _ema(macd_line, 9)
    window = closes[-20:]
    middle = mean(window)
    deviation = pstdev(window)
    true_ranges, plus_dm, minus_dm = [], [], []
    for i in range(1, len(candles)):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)
        true_ranges.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))
    atr14 = mean(true_ranges[-14:]) if true_ranges else 0.0
    atr_window = max(1, min(14, len(true_ranges)))
    atr_for_adx = mean(true_ranges[-atr_window:]) if true_ranges else 0.0
    if atr_for_adx > 0 and plus_dm and minus_dm:
        plus_di = 100.0 * mean(plus_dm[-atr_window:]) / atr_for_adx
        minus_di = 100.0 * mean(minus_dm[-atr_window:]) / atr_for_adx
        di_sum = plus_di + minus_di
        adx_proxy = 100.0 * abs(plus_di - minus_di) / di_sum if di_sum else 0.0
    else:
        plus_di = minus_di = adx_proxy = 0.0
    volume_window = volumes[-21:-1] if len(volumes) > 1 else []
    volume_average = mean(volume_window) if volume_window else 0.0
    volume_ratio = volumes[-1] / volume_average if volume_average > 0 else None
    bb_upper, bb_lower = middle + 2 * deviation, middle - 2 * deviation
    bb_width = (bb_upper - bb_lower) / middle * 100 if middle else 0.0
    bb_percent_b = (closes[-1] - bb_lower) / (bb_upper - bb_lower) if bb_upper > bb_lower else 0.5
    roc24 = (closes[-1] / closes[-25] - 1) * 100 if len(closes) > 24 and closes[-25] else None
    roc72 = (closes[-1] / closes[-73] - 1) * 100 if len(closes) > 72 and closes[-73] else None
    return {
        "rsi_14": round(_rsi(closes), 2),
        "ema_20": round(ema20[-1], 8),
        "ema_50": round(ema50[-1], 8),
        "ema_200": round(ema200[-1], 8) if len(closes) >= 200 else None,
        "macd": round(macd_line[-1], 8),
        "macd_signal": round(macd_signal[-1], 8),
        "macd_histogram": round(macd_line[-1] - macd_signal[-1], 8),
        "bollinger_upper": round(bb_upper, 8),
        "bollinger_middle": round(middle, 8),
        "bollinger_lower": round(bb_lower, 8),
        "bollinger_percent_b": round(bb_percent_b, 4),
        "bollinger_width_pct": round(bb_width, 4),
        "atr_14": round(atr14, 8),
        "atr_pct": round(atr14 / closes[-1] * 100, 4) if closes[-1] else 0.0,
        "adx_proxy_14": round(adx_proxy, 2),
        "plus_di_proxy_14": round(plus_di, 2),
        "minus_di_proxy_14": round(minus_di, 2),
        "volume_ratio_20": round(volume_ratio, 3) if volume_ratio is not None else None,
        "return_24h_pct": round(roc24, 4) if roc24 is not None else None,
        "return_72h_pct": round(roc72, 4) if roc72 is not None else None,
        "price_vs_ema20_pct": round((closes[-1] / ema20[-1] - 1) * 100, 4) if ema20[-1] else 0.0,
        "price_vs_ema50_pct": round((closes[-1] / ema50[-1] - 1) * 100, 4) if ema50[-1] else 0.0,
    }


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return round(ordered[lower] * (1 - fraction) + ordered[upper] * fraction, 4)



def _walk_forward_validation(closes: list[float], horizon_hours: int) -> dict:
    """Evaluate simple return baselines sequentially without using future labels.

    This is a small educational benchmark, not a trained trading model. Each
    test prediction uses only candles and fully matured historical outcomes
    available at that prediction origin.
    """
    min_train = max(48, horizon_hours * 4)
    origins = list(range(min_train, len(closes) - horizon_hours, max(1, horizon_hours)))
    if len(origins) < 5:
        return {
            "status": "insufficient_data",
            "test_windows": len(origins),
            "note": "برای ارزیابی مرحله‌ای، تاریخچهٔ بیشتری لازم است.",
            "models": [],
        }

    actuals, predictions = [], {"zero_return": [], "historical_mean": [], "momentum": []}
    for origin in origins:
        # Only outcomes whose full horizon ended before the current origin are known.
        train_returns = [
            (closes[j + horizon_hours] / closes[j] - 1.0) * 100.0
            for j in range(0, origin - horizon_hours + 1)
            if closes[j] > 0
        ]
        if not train_returns:
            continue
        actual = (closes[origin + horizon_hours] / closes[origin] - 1.0) * 100.0
        recent_start = max(0, origin - horizon_hours)
        momentum = (closes[origin] / closes[recent_start] - 1.0) * 100.0 if closes[recent_start] else 0.0
        actuals.append(actual)
        predictions["zero_return"].append(0.0)
        predictions["historical_mean"].append(mean(train_returns))
        predictions["momentum"].append(momentum)

    if len(actuals) < 5:
        return {"status": "insufficient_data", "test_windows": len(actuals), "models": []}

    models = []
    for name, preds in predictions.items():
        errors = [abs(p - a) for p, a in zip(preds, actuals)]
        direction_hits = sum((p > 0) == (a > 0) for p, a in zip(preds, actuals))
        models.append({
            "name": name,
            "mae_pct_points": round(mean(errors), 4),
            "directional_accuracy_pct": round(100.0 * direction_hits / len(actuals), 2),
            "test_windows": len(actuals),
        })
    models.sort(key=lambda item: item["mae_pct_points"])
    return {
        "status": "ok",
        "test_windows": len(actuals),
        "method": "expanding walk-forward; only matured past outcomes used for historical-mean baseline",
        "models": models,
        "note": "ارزیابی تاریخی است؛ به‌دلیل هم‌پوشانی افق‌ها و تغییر رژیم بازار، تضمینی برای آینده نیست.",
    }

def analyze(candles: list[dict], horizon_hours: int, target_pct: float) -> dict:
    if not 1 <= horizon_hours <= 168:
        raise ValueError("For this MVP, choose a horizon between 1 and 168 hours.")
    if not 0 <= target_pct <= 100:
        raise ValueError("Target return must be between 0 and 100 percent.")
    if len(candles) < 100:
        raise ValueError("At least 100 hourly candles are required for a stable indicator baseline.")
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    current = closes[-1]
    if current <= 0 or any(x <= 0 for x in closes):
        raise ValueError("Market data contains an invalid price.")

    outcomes = []
    for i in range(len(closes) - horizon_hours):
        start = closes[i]
        future_close = closes[i + horizon_hours]
        future_high = max(highs[i + 1:i + horizon_hours + 1])
        future_low = min(lows[i + 1:i + horizon_hours + 1])
        outcomes.append({
            "return_pct": (future_close / start - 1.0) * 100.0,
            "target_hit": future_high >= start * (1.0 + target_pct / 100.0),
            "drawdown_hit": future_low <= start * (1.0 - target_pct / 100.0),
        })
    if len(outcomes) < 20:
        raise ValueError("Not enough completed historical windows for this horizon.")

    returns = [x["return_pct"] for x in outcomes]
    up = sum(x > 0 for x in returns)
    down = sum(x < 0 for x in returns)
    target_hits = sum(x["target_hit"] for x in outcomes)
    downside_hits = sum(x["drawdown_hit"] for x in outcomes)
    indicators = _technical_indicators(candles)
    walk_forward = _walk_forward_validation(closes, horizon_hours)

    # Multi-factor score is a transparent heuristic, not a trained or calibrated model.
    score, reasons = 0, []
    def add(points: int, reason: str) -> None:
        nonlocal score
        score += points
        if points:
            reasons.append({"effect": "positive" if points > 0 else "negative", "points": points, "reason": reason})

    add(2 if current > indicators["ema_20"] > indicators["ema_50"] else
        -2 if current < indicators["ema_20"] < indicators["ema_50"] else 0,
        "قیمت و EMAهای ۲۰/۵۰ هم‌جهت‌اند" if current > indicators["ema_20"] > indicators["ema_50"] else
        "قیمت و EMAهای ۲۰/۵۰ نزولی‌اند" if current < indicators["ema_20"] < indicators["ema_50"] else
        "روند EMAهای کوتاه‌مدت هم‌جهت نیست")
    ema200 = indicators["ema_200"]
    add(2 if ema200 is not None and current > indicators["ema_50"] > ema200 else
        -2 if ema200 is not None and current < indicators["ema_50"] < ema200 else 0,
        "روند بلندمدت بالای EMA200 است" if ema200 is not None and current > indicators["ema_50"] > ema200 else
        "روند بلندمدت زیر EMA200 است" if ema200 is not None and current < indicators["ema_50"] < ema200 else
        "روند بلندمدت تأیید روشن ندارد")
    add(1 if indicators["macd_histogram"] > 0 else -1 if indicators["macd_histogram"] < 0 else 0,
        "هیستوگرام MACD مثبت است" if indicators["macd_histogram"] > 0 else "هیستوگرام MACD منفی است")
    rsi = indicators["rsi_14"]
    add(1 if 52 <= rsi <= 68 else -1 if rsi < 45 or rsi > 75 else 0,
        "مومنتوم RSI نسبتاً مثبت است" if 52 <= rsi <= 68 else
        "RSI ضعف یا داغ‌شدن بیش‌ازحد مومنتوم را نشان می‌دهد" if rsi < 45 or rsi > 75 else
        "RSI سیگنال پرقدرتی نمی‌دهد")
    roc24 = indicators["return_24h_pct"]
    add(1 if roc24 is not None and roc24 > 0.5 else -1 if roc24 is not None and roc24 < -0.5 else 0,
        "بازده ۲۴ ساعت اخیر مثبت است" if roc24 is not None and roc24 > 0.5 else
        "بازده ۲۴ ساعت اخیر منفی است" if roc24 is not None and roc24 < -0.5 else
        "تغییر ۲۴ ساعت اخیر محدود است")
    volume_ratio = indicators["volume_ratio_20"]
    if volume_ratio is not None and volume_ratio >= 1.2 and roc24 is not None and abs(roc24) >= 0.5:
        add(1 if roc24 > 0 else -1, "حجم بالاتر از میانگین، حرکت اخیر را همراهی می‌کند")
    score = max(-100, min(100, round(score / 8 * 100)))
    if score >= 35:
        technical_bias = "تمایل صعودی (غیرقطعی)"
    elif score <= -35:
        technical_bias = "تمایل نزولی (غیرقطعی)"
    else:
        technical_bias = "خنثی / سیگنال‌های متناقض"
    if indicators["adx_proxy_14"] >= 25:
        regime = "رونددارتر"
    elif indicators["bollinger_width_pct"] >= 8:
        regime = "نوسان بالا"
    else:
        regime = "کم‌روند یا فشرده"
    return {
        "price": current, "currency": "USDT", "horizon_hours": horizon_hours, "target_pct": target_pct,
        "sample_count": len(outcomes), "probability_up": _safe_percent(up, len(outcomes)),
        "probability_down": _safe_percent(down, len(outcomes)),
        "probability_target_hit": _safe_percent(target_hits, len(outcomes)),
        "probability_negative_return": _safe_percent(down, len(outcomes)),
        "probability_downside_target_hit": _safe_percent(downside_hits, len(outcomes)),
        "mean_return_pct": round(mean(returns), 4), "return_volatility_pct": round(pstdev(returns), 4),
        "historical_return_p10_pct": _quantile(returns, 0.10),
        "historical_return_median_pct": _quantile(returns, 0.50),
        "historical_return_p90_pct": _quantile(returns, 0.90),
        "indicators": indicators,
        "walk_forward_validation": walk_forward,
        "technical_bias": technical_bias,
        "technical_score": score,
        "market_regime": regime,
        "signal_reasons": reasons,
        "decision_hint": "این امتیاز ترکیبیِ اکتشافی از شاخص‌های تکنیکال است، نه احتمال واقعیِ رشد یا توصیهٔ خرید/فروش. هزینه‌ها، نقدشوندگی و اخبار در آن لحاظ نشده‌اند.",
        "target_hit_count": target_hits,
        "target_zero_explanation": (
            "در نمونه‌های تاریخی بررسی‌شده، هیچ بازه‌ای به این هدف نرسیده؛ احتمال تجربی صفر است، نه اثباتِ ناممکن‌بودن."
            if target_hits == 0 else None
        ),
        "method": "Historical frequencies + multi-factor technical heuristic (EMA, MACD, RSI, volume, volatility)",
        "warning": "برآوردها توصیفی‌اند؛ پنجره‌های تاریخی هم‌پوشانی دارند و بنابراین نمونه‌ها مستقل نیستند. امتیاز تکنیکال احتمال کالیبره‌شده نیست و هیچ‌کدام نتیجه آینده را تضمین نمی‌کنند.",
    }
