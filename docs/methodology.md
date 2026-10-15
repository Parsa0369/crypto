# Methodology and limitations

## Current MVP
The dashboard downloads public hourly OHLCV candles and reports historical frequencies for completed rolling windows of the selected horizon. It also computes a basic RSI(14). This is a transparent descriptive baseline, **not a trained machine-learning model**, not a calibrated probability forecast, and not a trading signal.

## Definitions
- **Historical up frequency:** share of completed windows whose closing price ended above the starting close.
- **Historical down frequency:** share of completed windows whose closing price ended below the starting close.
- **Target-touch frequency:** share of completed windows where at least one observed hourly high reached the selected target above the starting close.
- **Negative-return frequency:** share of completed windows whose closing price ended below the starting close.
- **Return volatility:** population standard deviation of the historical window returns.

Target-touch and negative-return events can both happen during the same window; they are not complementary outcomes. Hourly candles cannot resolve price movement inside each candle or show the exact order of intrabar events.

## Statistical limitations
- Adjacent rolling windows overlap heavily, so sample counts are not independent observations.
- Recent history may not represent future market regimes.
- Fees, spread, slippage, liquidity, funding, and taxes are not included.
- A target of 0% is not a meaningful profit objective.
- The provider can rate-limit or change its API.
- Historical frequencies must not be presented as reliable forward probabilities until evaluated on strictly out-of-sample data and calibrated.
- No trading or wallet access is implemented.

## Future evaluation plan
1. Use time-ordered train/validation/test splits.
2. Compare against simple baselines.
3. Prevent look-ahead and survivorship bias.
4. Evaluate Brier score, log loss, reliability diagrams, and performance by regime.
5. Account for transaction costs and test with paper trading before considering any real-money use.
