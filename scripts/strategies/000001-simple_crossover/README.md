# 000001 – Simple SMA Crossover Strategy

This strategy implements a classic Simple Moving Average (SMA) crossover for EURUSD on M5 data.
It serves as a minimal, production-ready example built on top of the shared utilities in `scripts/strategies/strategy_base.py`.

## How it works
- **Indicators**: Two SMAs are computed – a fast SMA (default 20) and a slow SMA (default 50).
- **Signals**:
  - Buy when `sma_fast > sma_slow` and there are no open positions (flat).
  - Close BUY when a bearish crossover happens (or when rules indicate exit).
  - Sell when `sma_fast < sma_slow` and there are no open positions (flat).
  - Close SELL on bullish crossover.
- **Execution**: Uses the backtest operation environment to place market orders and to close positions.

## File entry point
- Script: `simple_crossover_backtest.py`
- Function: `main()`

## Shared utilities used
The strategy relies on the following helpers from `strategy_base.py`:
- **login_live_and_backtest()**: Logs into live for data access and creates an isolated backtest environment.
- **build_operations_dataframe()**: Converts `history_deals` into a normalized DataFrame, including costs (swap/commission).
- **compute_statistics()**: Produces performance metrics from the operations DataFrame and backtest state.
- **render_markdown_report()**: Renders a complete Markdown report from computed stats and strategy params.
- **save_report_markdown()**: Saves the Markdown report next to the strategy script.
- **DEFAULT_CREDENTIALS**: Centralized demo credentials used by examples and templates (edit in `strategy_base.py`).

## Parameters
- Symbol: `EURUSD`
- Timeframe: `M5`
- Candles: `10,000` (downloaded using the live connection)
- SMA Fast: `20`
- SMA Slow: `50`

You can tweak these directly in `simple_crossover_backtest.py`.

## Outputs
- Console summary with costs and key metrics.
- A Markdown report saved next to the script, e.g.:
  - `scripts/strategies/000001-simple_crossover/backtest_results_EURUSD_YYYYMMDD_HHMMSS.md`
  - Includes: Win rate, Profit factor, Sharpe, Drawdown, Recovery factor, Equity stats, Costs, and Parameters.

## How to run
Use your Conda environment preference:

```bash
conda run -n backtestenv python scripts/strategies/000001-simple_crossover/simple_crossover_backtest.py
```

## Customize
- Adjust SMA window sizes (`fast`, `slow`) and symbol/timeframe.
- Replace the signal logic to test variations (e.g., add filters or risk management rules).
- Add extra sections to the Markdown by using `render_markdown_report(..., extra_sections={ ... })` if migrating this strategy to the higher-level `strategy_template.py` approach.

## Notes
- All stats consider costs where applicable (swap and commission).
- Initial balance and leverage are set via `login_live_and_backtest()`; edit as needed.
- Credentials are centralized in `strategy_base.DEFAULT_CREDENTIALS`.
