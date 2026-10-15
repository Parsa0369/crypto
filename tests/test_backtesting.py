import math
import unittest

from backend.backtesting import run_ema_backtest


class BacktestingTests(unittest.TestCase):
    def test_requires_sufficient_history(self):
        with self.assertRaises(ValueError):
            run_ema_backtest([{"close": 100 + i} for i in range(30)])

    def test_returns_summary_and_equity_curve(self):
        candles = [
            {"close": 100 + 0.03 * i + 5 * math.sin(i / 7)}
            for i in range(180)
        ]
        result = run_ema_backtest(candles, fee_pct=0.1)

        self.assertEqual(result["candles"], 180)
        self.assertIn("strategy_return_pct", result)
        self.assertIn("buy_and_hold_return_pct", result)
        self.assertIn("max_drawdown_pct", result)
        self.assertTrue(result["equity_curve"])
        self.assertLessEqual(result["max_drawdown_pct"], 100)
        self.assertGreaterEqual(result["max_drawdown_pct"], 0)
        self.assertIn("trades", result)

    def test_fee_parameter_is_reported(self):
        candles = [
            {"close": 100 + 0.03 * i + 5 * math.sin(i / 7)}
            for i in range(180)
        ]
        result = run_ema_backtest(candles, fee_pct=0.2)
        self.assertEqual(result["fee_pct_per_side"], 0.2)


if __name__ == "__main__":
    unittest.main()
