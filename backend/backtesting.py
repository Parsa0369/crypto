"""Educational, long-only EMA crossover backtest.

This module is an independent implementation inspired by common backtesting
workflows. It does not import or copy Freqtrade code and never places orders.
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
    """Backtest an EMA(12)/EMA(26) crossover on completed hourly closes.

    A position enters on a bullish cross and exits on a bearish cross. Fees are
    charged on both entry and exit. No leverage, shorting, or live orders.
    """
    if not 0 <= fee_pct <= 2:
        raise ValueError("fee_pct must be between 0 and 2")
    closes = [float(c["close"]) for c in candles if float(c.get("close", 0)) > 0]
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
    equity_curve = []
    trades = []
    previous_difference = fast[0] - slow[0]

    # Start after warm-up; act on close-to-close crossover observations.
    for i in range(1, len(closes)):
        difference = fast[i] - slow[i]
        if not position and previous_difference <= 0 < difference:
            position = True
            entry_price = closes[i]
            entry_index = i
            equity *= (1.0 - fee)
        elif position and previous_difference >= 0 > difference:
            exit_price = closes[i]
            gross_return = exit_price / entry_price - 1.0
            net_return = (1.0 - fee) * (exit_price / entry_price) * (1.0 - fee) - 1.0
            equity *= (1.0 + gross_return) * (1.0 - fee)
            # Entry fee was already deducted above.
            trades.append({
                "entry_index": entry_index,
                "exit_index": i,
                "entry_price": round(entry_price, 8),
                "exit_price": round(exit_price, 8),
                "return_pct": round(net_return * 100.0, 4),
                "duration_hours": i - entry_index,
            })
            position = False
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak if peak else 0.0)
        if i % max(1, len(closes) // 60) == 0 or i == len(closes) - 1:
            equity_curve.append({"index": i, "equity": round(equity * 100.0, 4)})

        previous_difference = difference

    if position:
        exit_price = closes[-1]
        gross_return = exit_price / entry_price - 1.0
        net_return = (1.0 - fee) * (exit_price / entry_price) * (1.0 - fee) - 1.0
        equity *= (1.0 + gross_return) * (1.0 - fee)
        trades.append({
            "entry_index": entry_index,
            "exit_index": len(closes) - 1,
            "entry_price": round(entry_price, 8),
            "exit_price": round(exit_price, 8),
            "return_pct": round(net_return * 100.0, 4),
            "duration_hours": len(closes) - 1 - entry_index,
            "open_at_end": True,
        })

    returns = [t["return_pct"] for t in trades]
    benchmark = (closes[-1] / closes[0] - 1.0) * 100.0
    return {
        "strategy": "EMA 12/26 crossover (long-only)",
        "candles": len(closes),
        "fee_pct_per_side": fee_pct,
        "strategy_return_pct": round((equity - 1.0) * 100.0, 4),
        "buy_and_hold_return_pct": round(benchmark, 4),
        "max_drawdown_pct": round(max_drawdown * 100.0, 4),
        "trade_count": len(trades),
        "win_rate_pct": round(100.0 * sum(x > 0 for x in returns) / len(returns), 2) if returns else None,
        "average_trade_return_pct": round(mean(returns), 4) if returns else None,
        "equity_curve": equity_curve,
        "trades": trades[-20:],
        "note": "نتیجهٔ تاریخی و آموزشی است؛ کارمزد واقعی، اسپرد، لغزش قیمت و کیفیت اجرای سفارش ممکن است متفاوت باشد. هیچ سفارشی ارسال نمی‌شود.",
    }
