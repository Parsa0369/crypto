"""Educational, long-only EMA crossover backtest.

Independent implementation inspired by common backtesting workflows.
No Freqtrade source is copied or imported, and no orders are ever placed.
"""
from __future__ import annotations

from statistics import mean


def _ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1.0 - alpha) * result[-1])
    return result


def run_ema_backtest(candles: list[dict], fee_pct: float = 0.1) -> dict:
    """Simulate EMA(12)/EMA(26) crossover entries/exits on hourly closes.

    Entry and exit fees are applied to compounded equity. Open positions are
    marked to market for drawdown measurements. No leverage or shorting.
    """
    if not 0 <= fee_pct <= 2:
        raise ValueError("fee_pct must be between 0 and 2")
    closes = [
        float(c["close"])
        for c in candles
        if float(c.get("close", 0) or 0) > 0
    ]
    if len(closes) < 60:
        raise ValueError("حداقل ۶۰ کندل معتبر برای بک‌تست لازم است.")

    fast, slow = _ema(closes, 12), _ema(closes, 26)
    fee = fee_pct / 100.0
    position = False
    entry_price = 0.0
    entry_index = 0
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    equity_curve = [{"index": 0, "equity": 100.0}]
    trades = []
    previous_difference = fast[0] - slow[0]
    stride = max(1, len(closes) // 60)

    for i in range(1, len(closes)):
        difference = fast[i] - slow[i]

        if not position and previous_difference <= 0 < difference:
            position = True
            entry_price = closes[i]
            entry_index = i
            equity *= 1.0 - fee  # Entry fee.
        elif position and previous_difference >= 0 > difference:
            exit_price = closes[i]
            net_return = (1.0 - fee) * (exit_price / entry_price) * (1.0 - fee) - 1.0
            equity *= (exit_price / entry_price) * (1.0 - fee)
            trades.append({
                "entry_index": entry_index,
                "exit_index": i,
                "entry_price": round(entry_price, 8),
                "exit_price": round(exit_price, 8),
                "return_pct": round(net_return * 100.0, 4),
                "duration_hours": i - entry_index,
            })
            position = False

        marked_equity = equity * (closes[i] / entry_price) if position else equity
        peak = max(peak, marked_equity)
        if peak:
            max_drawdown = max(max_drawdown, (peak - marked_equity) / peak)

        if i % stride == 0 or i == len(closes) - 1:
            equity_curve.append({"index": i, "equity": round(marked_equity * 100.0, 4)})
        previous_difference = difference

    if position:
        exit_price = closes[-1]
        net_return = (1.0 - fee) * (exit_price / entry_price) * (1.0 - fee) - 1.0
        equity *= (exit_price / entry_price) * (1.0 - fee)
        trades.append({
            "entry_index": entry_index,
            "exit_index": len(closes) - 1,
            "entry_price": round(entry_price, 8),
            "exit_price": round(exit_price, 8),
            "return_pct": round(net_return * 100.0, 4),
            "duration_hours": len(closes) - 1 - entry_index,
            "open_at_end": True,
        })
        peak = max(peak, equity)
        if peak:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
        if equity_curve:
            equity_curve[-1]["equity"] = round(equity * 100.0, 4)

    returns = [trade["return_pct"] for trade in trades]
    benchmark = (closes[-1] / closes[0] - 1.0) * 100.0
    return {
        "strategy": "EMA 12/26 crossover (long-only)",
        "candles": len(closes),
        "fee_pct_per_side": fee_pct,
        "strategy_return_pct": round((equity - 1.0) * 100.0, 4),
        "buy_and_hold_return_pct": round(benchmark, 4),
        "max_drawdown_pct": round(max_drawdown * 100.0, 4),
        "trade_count": len(trades),
        "win_rate_pct": round(100.0 * sum(value > 0 for value in returns) / len(returns), 2) if returns else None,
        "average_trade_return_pct": round(mean(returns), 4) if returns else None,
        "equity_curve": equity_curve,
        "trades": trades[-20:],
        "note": "نتیجهٔ تاریخی و آموزشی است؛ کارمزد واقعی، اسپرد، لغزش قیمت و کیفیت اجرای سفارش ممکن است متفاوت باشد. هیچ سفارشی ارسال نمی‌شود.",
    }
