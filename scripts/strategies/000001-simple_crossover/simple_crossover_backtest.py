from __future__ import annotations

from datetime import timezone
import pandas as pd
import numpy as np
import logging
import sys
import os

# Disable all loggers
for logger in logging.root.manager.loggerDict.values():
    if isinstance(logger, logging.Logger):
        logger.setLevel(logging.CRITICAL)

# Configure basic logging for immediate output
logging.basicConfig(level=logging.CRITICAL, force=True, handlers=[
    logging.StreamHandler()
])

# Force flush for prints
sys.stdout.reconfigure(line_buffering=True)

from algo_trading.sources.MetaTrader5_source.account.account import Account
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,
    ENUM_ACCOUNT_TRADE_MODE,
    ENUM_ACCOUNT_STOPOUT_MODE,
    ENUM_ACCOUNT_MARGIN_MODE,
    ENUM_POSITION_TYPE,
    ENUM_TIMEFRAME,
)
from algo_trading.sources.MetaTrader5_source.rates import Rates

# Make shared strategy utilities importable
_STRAT_DIR = os.path.dirname(os.path.dirname(__file__))  # scripts/strategies
if _STRAT_DIR not in sys.path:
    sys.path.append(_STRAT_DIR)
from strategy_base import (
    DEFAULT_CREDENTIALS,
    login_live_and_backtest,
    build_operations_dataframe,
    compute_statistics,
    render_markdown_report,
    save_report_markdown,
)


# Credenciais centralizadas em strategy_base.DEFAULT_CREDENTIALS


def main():
    # 1) Login live e criar ambiente de backtest via base
    creds = DEFAULT_CREDENTIALS
    account, backtest, operation = login_live_and_backtest(
        login=creds.login,
        server=creds.server,
        password=creds.password,
        path=creds.path,
        balance=10_000,
        leverage=100,
    )

    # 3) Configure symbols and fetch real OHLC data
    symbol = "EURUSD"
    operation.backtest_add_symbol_data([symbol])

    # Fetch last N candles on a timeframe using Rates (requires live connection)
    timeframe = ENUM_TIMEFRAME.TIMEFRAME_M5
    n_candles = 10000
    df = Rates.get_last_n_candles(
        symbol=symbol,
        timeframe=timeframe,
        n_candles=n_candles,
        use_close_candle_time=False,
    )

    # 4) Indicators: Simple Moving Averages
    fast = 20
    slow = 50
    df["sma_fast"] = df["close"].rolling(fast).mean()
    df["sma_slow"] = df["close"].rolling(slow).mean()

    # Utility helpers
    def current_position_type():
        if not backtest.positions:
            return None
        return backtest.positions[0].type

    def flat():
        return len(backtest.positions) == 0

    # 5) Backtest loop: update candles and act on SMA crossovers
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

        # Update environment (decorator triggers trading events)
        operation.backtest_update_candles({symbol: last_candle})
        # Force-set last_candle in table to avoid None/NaN edge cases during validation
        try:
            operation.backtest_symbols_data.at[symbol, "last_candle"] = last_candle
        except Exception:
            pass

        # Ensure last_candle is properly set in the backtest symbols table before trading
        try:
            _row = operation.backtest_symbols_data.loc[symbol]
            _lc = _row.get("last_candle")
            has_last = isinstance(_lc, pd.Series) and (not _lc.empty) and all(k in _lc for k in ("open","high","low","close"))
        except Exception:
            has_last = False
        if not has_last:
            # skip this tick until environment reflects last_candle
            continue

        sma_f = row["sma_fast"]
        sma_s = row["sma_slow"]
        if pd.isna(sma_f) or pd.isna(sma_s):
            continue

        pos = current_position_type()
        bullish = sma_f > sma_s
        bearish = sma_f < sma_s

        if bullish and flat():
            operation.buy(symbol=symbol, volume=1.0, comment=f"SMA{fast}>{slow}")
        elif bearish and not flat() and pos == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
            operation.close_all_positions(comment="Cross down")
        elif bearish and flat():
            operation.sell(symbol=symbol, volume=1.0, comment=f"SMA{fast}<{slow}")
        elif bullish and not flat() and pos == ENUM_POSITION_TYPE.POSITION_TYPE_SELL:
            operation.close_all_positions(comment="Cross up")

    # 6) Close any open positions to finalize PnL
    if backtest.positions:
        operation.close_all_positions(comment="End of backtest - flatten")

    # 7) Estado final (opcional)
    print("Balance:", backtest.balance, flush=True)
    print("Equity:", backtest.equity, flush=True)
    print("Positions open:", len(backtest.positions), flush=True)
    print("Pending orders:", len(backtest.orders), flush=True)
    sys.stdout.flush()

    # 8) Estatísticas e relatório via base
    deals = backtest.history_deals or []
    ops_df, _ = build_operations_dataframe(deals)
    stats = compute_statistics(ops_df, backtest=backtest, initial_balance=10_000)

    params = {
        "symbol": symbol,
        "timeframe_name": timeframe.name,
        "fast": fast,
        "slow": slow,
    }
    md = render_markdown_report(stats=stats, params=params)
    out_path = save_report_markdown(md, script_file=__file__, symbol=symbol)
    print(f"\nBacktest results saved to: {out_path}")


if __name__ == "__main__":
    main()
