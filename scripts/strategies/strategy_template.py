from __future__ import annotations

"""
Strategy Template

Use this file as a base for creating new strategies. It demonstrates:
- Logging into live to fetch data and creating a backtest environment
- Running a loop to update candles and generate trading signals
- Computing stats and saving a Markdown report (with optional extra sections)

Rename this file and implement your custom signal logic in `generate_signals()`.
"""

from typing import Dict, Any
import sys
import logging
import pandas as pd

# Silence third-party loggers during backtests
for logger in logging.root.manager.loggerDict.values():
    if isinstance(logger, logging.Logger):
        logger.setLevel(logging.CRITICAL)

# Force flush for prints
sys.stdout.reconfigure(line_buffering=True)

from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_POSITION_TYPE,
    ENUM_TIMEFRAME,
)
from algo_trading.sources.MetaTrader5_source.rates import Rates

from .strategy_base import (
    login_live_and_backtest,
    build_operations_dataframe,
    compute_statistics,
    render_markdown_report,
    save_report_markdown,
    DEFAULT_CREDENTIALS,
)


# Credentials are provided centrally in strategy_base.DEFAULT_CREDENTIALS


def generate_signals(row: pd.Series, state: Dict[str, Any]) -> Dict[str, Any]:
    """Implement your strategy's signal logic here.
    Return one of: {"buy": True}, {"sell": True}, {"close_all": True}, or {}.

    This default template implements a simple SMA crossover as example.
    """
    sma_fast = row.get("sma_fast")
    sma_slow = row.get("sma_slow")
    if pd.isna(sma_fast) or pd.isna(sma_slow):
        return {}

    pos_type = state.get("current_pos_type")
    bullish = sma_fast > sma_slow
    bearish = sma_fast < sma_slow

    if bullish and state.get("is_flat", True):
        return {"buy": True}
    if bearish and pos_type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
        return {"close_all": True}
    if bearish and state.get("is_flat", True):
        return {"sell": True}
    if bullish and pos_type == ENUM_POSITION_TYPE.POSITION_TYPE_SELL:
        return {"close_all": True}

    return {}


def run_strategy():
    # 1) Login and set up backtest
    creds = DEFAULT_CREDENTIALS
    account, backtest, operation = login_live_and_backtest(
        login=creds.login,
        server=creds.server,
        password=creds.password,
        path=creds.path,
        balance=10_000,
        leverage=100,
    )

    # 2) Configure symbols and fetch OHLC
    symbol = "EURUSD"
    operation.backtest_add_symbol_data([symbol])

    timeframe = ENUM_TIMEFRAME.TIMEFRAME_M5
    n_candles = 10_000
    df = Rates.get_last_n_candles(
        symbol=symbol,
        timeframe=timeframe,
        n_candles=n_candles,
        use_close_candle_time=False,
    )

    # Example indicators for the template (can be removed/replaced)
    fast = 20
    slow = 50
    df["sma_fast"] = df["close"].rolling(fast).mean()
    df["sma_slow"] = df["close"].rolling(slow).mean()

    def current_position_type():
        if not backtest.positions:
            return None
        return backtest.positions[0].type

    def flat():
        return len(backtest.positions) == 0

    # 3) Main loop
    for ts, row in df.iterrows():
        last_candle = pd.Series(
            {
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            },
            name=ts,
        )

        # Update environment
        operation.backtest_update_candles({symbol: last_candle})
        try:
            operation.backtest_symbols_data.at[symbol, "last_candle"] = last_candle
        except Exception:
            pass

        # Ensure ready
        try:
            _row = operation.backtest_symbols_data.loc[symbol]
            _lc = _row.get("last_candle")
            has_last = isinstance(_lc, pd.Series) and (not _lc.empty) and all(k in _lc for k in ("open","high","low","close"))
        except Exception:
            has_last = False
        if not has_last:
            continue

        # Query state and decide
        state = {
            "current_pos_type": current_position_type(),
            "is_flat": flat(),
        }
        action = generate_signals(row, state)

        if action.get("buy"):
            operation.buy(symbol=symbol, volume=1.0, comment=f"TEMPLATE-BUY")
        elif action.get("sell"):
            operation.sell(symbol=symbol, volume=1.0, comment=f"TEMPLATE-SELL")
        elif action.get("close_all"):
            operation.close_all_positions(comment="TEMPLATE-CLOSE")

    # 4) Finalize and stats
    if backtest.positions:
        operation.close_all_positions(comment="End of backtest - flatten")

    deals = backtest.history_deals or []
    ops_df, costs = build_operations_dataframe(deals)

    stats = compute_statistics(ops_df, backtest=backtest, initial_balance=10_000)

    # Example extra section a strategy could add
    extra_sections = {
        "Template Extra": "This section can include any custom metrics or notes specific to the strategy.",
    }

    params = {
        "symbol": symbol,
        "timeframe_name": timeframe.name,
        "fast": fast,
        "slow": slow,
    }

    md = render_markdown_report(stats=stats, params=params, extra_sections=extra_sections)

    # Save report next to this script
    out_path = save_report_markdown(md, script_file=__file__, symbol=symbol)
    print(f"\nBacktest results saved to: {out_path}")


if __name__ == "__main__":
    # Prefer running via Conda env: conda run -n backtestenv python scripts/strategies/strategy_template.py
    run_strategy()
