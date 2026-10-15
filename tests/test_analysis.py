import unittest
from backend.analysis import analyze


def sample_candles(count=260):
    candles, price = [], 100.0
    for i in range(count):
        price *= 1.001 if i % 3 else 0.999
        candles.append({"open_time": i * 3600000, "open": price, "high": price * 1.01,
                        "low": price * 0.99, "close": price, "volume": 1000.0})
    return candles


class AnalysisTests(unittest.TestCase):
    def test_estimates_are_bounded(self):
        result = analyze(sample_candles(), 6, 5)
        for key in ("probability_up", "probability_down", "probability_target_hit", "probability_negative_return"):
            self.assertGreaterEqual(result[key], 0)
            self.assertLessEqual(result[key], 100)
        self.assertGreater(result["sample_count"], 20)

    def test_invalid_horizon_rejected(self):
        with self.assertRaises(ValueError):
            analyze(sample_candles(), 0, 5)

    def test_invalid_target_rejected(self):
        with self.assertRaises(ValueError):
            analyze(sample_candles(), 6, 101)


if __name__ == "__main__":
    unittest.main()
