from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd
import numpy as np
import logging
import sys
import os
import pickle

# Silence third-party loggers during backtests
for logger in logging.root.manager.loggerDict.values():
    if isinstance(logger, logging.Logger):
        logger.setLevel(logging.CRITICAL)

# Force flush for prints
sys.stdout.reconfigure(line_buffering=True)

# Strategy configuration (module-level)
ZVIG_ATR_FLOOR: float = float(os.getenv("ZVIG_ATR_FLOOR", "0.00035"))
ZVIG_MODE: str = os.getenv("ZVIG_MODE", "TURBO").upper()

from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_POSITION_TYPE,
    ENUM_TIMEFRAME,
    ENUM_DEAL_REASON,
    ENUM_DEAL_ENTRY,
    ENUM_DEAL_TYPE,
)
from algo_trading.sources.MetaTrader5_source.rates import Rates
from algo_trading.sources.MetaTrader5_source.utils.exceptions import InsufficientMarginError

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


def rolling_zscore(x: pd.Series, window: int) -> pd.Series:
    mean = x.rolling(window).mean()
    std = x.rolling(window).std(ddof=0)
    return (x - mean) / std.replace(0, np.nan)


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr1 = (df["high"] - df["low"]).abs()
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    tr = true_range(df)
    return tr.rolling(length).mean()


def bollinger_bandwidth(df: pd.DataFrame, length: int = 20, stdev: float = 2.0) -> pd.Series:
    ma = df["close"].rolling(length).mean()
    sd = df["close"].rolling(length).std(ddof=0)
    upper = ma + stdev * sd
    lower = ma - stdev * sd
    return (upper - lower) / df["close"]


def session_vwap(df: pd.DataFrame) -> pd.Series:
    # VWAP reset by UTC day
    day = df.index.tz_convert(timezone.utc).date
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    vol = df.get("tick_volume", pd.Series(1.0, index=df.index))
    cum_tp_vol = tp.groupby(day).apply(lambda s: s.cumsum())
    cum_vol = vol.groupby(day).apply(lambda s: s.cumsum())
    # Re-align to original index
    cum_tp_vol.index = df.index
    cum_vol.index = df.index
    return cum_tp_vol / cum_vol.replace(0, np.nan)


def percentile_rank(series: pd.Series, window: int) -> pd.Series:
    # Percentile rank of the last value within the rolling window
    def _rank(arr: np.ndarray) -> float:
        if len(arr) == 0 or np.isnan(arr[-1]):
            return np.nan
        last = arr[-1]
        valid = arr[~np.isnan(arr)]
        if len(valid) == 0:
            return np.nan
        return (np.sum(valid <= last) - 1) / max(len(valid) - 1, 1)

    return series.rolling(window).apply(lambda a: _rank(a), raw=True)


def kama(series: pd.Series, length: int = 50, fast: int = 2, slow: int = 30) -> pd.Series:
    # Kaufman Adaptive Moving Average (simple implementation)
    change = series.diff(length).abs()
    volatility = series.diff().abs().rolling(length).sum()
    er = change / volatility.replace(0, np.nan)
    sc = (er * (2 / (fast + 1) - 2 / (slow + 1)) + 2 / (slow + 1)) ** 2
    kama_vals = [np.nan] * len(series)
    if len(series) > 0:
        kama_vals[length - 1] = series.iloc[length - 1]
    for i in range(length, len(series)):
        prev = kama_vals[i - 1] if not np.isnan(kama_vals[i - 1]) else series.iloc[i - 1]
        kama_vals[i] = prev + sc.iloc[i] * (series.iloc[i] - prev)
    return pd.Series(kama_vals, index=series.index)


def main():
    # 1) Login and backtest env
    creds = DEFAULT_CREDENTIALS
    account, backtest, operation = login_live_and_backtest(
        login=creds.login,
        server=creds.server,
        password=creds.password,
        path=creds.path,
        balance=10_000,
        leverage=100,
    )

    # 2) Configure symbol and fetch data
    symbol = "EURUSD"
    operation.backtest_add_symbol_data([symbol])

    tf5 = ENUM_TIMEFRAME.TIMEFRAME_M5
    tf1h = ENUM_TIMEFRAME.TIMEFRAME_H1

    # Use only the last N candles (within terminal maxbars limit)
    n_candles = 40_000
    df5 = Rates.get_last_n_candles(symbol=symbol, timeframe=tf5, n_candles=n_candles, use_close_candle_time=False)
    df1h = Rates.get_last_n_candles(symbol=symbol, timeframe=tf1h, n_candles=max(1200, n_candles // 12), use_close_candle_time=False)

    if df5.empty or df1h.empty:
        raise ValueError("Failed to fetch data for symbol")

    # For reporting purposes
    date_from = f"LAST_{n_candles}"
    date_to = "NOW"

    # 3) Indicators (Z-VIG core)
    df5 = df5.copy()
    df5["atr14"] = atr(df5, 14)
    df5["atr_pct"] = df5["atr14"] / df5["close"]
    df5["bbw20"] = bollinger_bandwidth(df5, 20, 2.0)
    df5["tr"] = true_range(df5)
    df5["tr_med20"] = df5["tr"].rolling(20).median()

    vwap_sess = session_vwap(df5)
    dev = df5["close"] - vwap_sess
    df5["z50"] = rolling_zscore(dev, 50)

    # Rolling percent ranks (approximation of session-based ranks)
    # 5m: ~288 barras/dia. Aqui usamos ~2.5 dias p/ BBW e ~7 dias p/ ATR_pct.
    win_bbw = min(720, len(df5))
    win_atr = min(2000, len(df5))
    df5["p_bbw"] = percentile_rank(df5["bbw20"], window=max(win_bbw, 200))
    df5["p_atr"] = percentile_rank(df5["atr_pct"], window=max(win_atr, 400))

    # Se ainda houver NaN no início, trate como "passa" (libera o portão de vol/BBW)
    df5["p_bbw"] = df5["p_bbw"].fillna(0.5)
    df5["p_atr"]  = df5["p_atr"].fillna(0.5)

    # 1h KAMA and slope aligned to 5m
    df1h = df1h.copy()
    df1h["kama50"] = kama(df1h["close"], 50)
    df1h["kama_slope"] = df1h["kama50"].diff(5)

    # Align 1h to 5m using merge_asof
    df1h_idx = df1h.reset_index().rename(columns={"index": "time"})
    df5_idx = df5.reset_index().rename(columns={"index": "time"})
    merged = pd.merge_asof(df5_idx.sort_values("time"), df1h_idx[["time","kama50","kama_slope"]].sort_values("time"), on="time", direction="backward")
    df5["kama50"] = merged["kama50"].values
    df5["kama_slope"] = merged["kama_slope"].values
    # Fallbacks para não ficar semanas sem KAMA (objetivo e seguro)
    df5["kama50"] = df5["kama50"].fillna(df5["close"].rolling(60).mean())
    df5["kama50"] = df5["kama50"].bfill()

    # Mode configuration (includes TURBO + req_hits for 3-of-4 gating)
    mode = ZVIG_MODE
    cfg_map = {
        "STRICT": {"atr_min": 0.35, "atr_max": 0.85, "tr_mul": 1.20, "bbw_prev_max": 0.25, "bbw_min": 0.35, "z_abs": 1.60, "body_min_atr": 0.30, "thrust_lb": 3, "req_hits": 4, "cooldown_bars": 3, "time_exit_max": 40},
        "MEDIUM": {"atr_min": 0.30, "atr_max": 0.90, "tr_mul": 1.10, "bbw_prev_max": 0.30, "bbw_min": 0.50, "z_abs": 1.40, "body_min_atr": 0.25, "thrust_lb": 3, "req_hits": 3, "cooldown_bars": 4, "time_exit_max": 35},
        "LITE":   {"atr_min": 0.25, "atr_max": 0.95, "tr_mul": 1.05, "bbw_prev_max": 0.30, "bbw_min": 0.40, "z_abs": 1.20, "body_min_atr": 0.20, "thrust_lb": 3, "req_hits": 2, "cooldown_bars": 2, "time_exit_max": 25},
        "TURBO":  {"atr_min": 0.05, "atr_max": 0.99, "tr_mul": 1.01, "bbw_prev_max": 0.40, "bbw_min": 0.45, "z_abs": 0.60, "body_min_atr": 0.00, "thrust_lb": 2, "req_hits": 2, "cooldown_bars": 2, "time_exit_max": 25},
    }
    config = cfg_map.get(mode, cfg_map["TURBO"])
    atr_min = config["atr_min"]; atr_max = config["atr_max"]
    tr_mul = config["tr_mul"]; bbw_prev_max = config["bbw_prev_max"]; bbw_min = config["bbw_min"]
    z_abs = config["z_abs"]; body_min_atr = config["body_min_atr"]; thrust_lb = config["thrust_lb"]
    req_hits = config["req_hits"]
    cooldown_bars = config["cooldown_bars"]
    time_exit_max = config["time_exit_max"]
    df5["roll_high"] = df5["high"].shift(1).rolling(thrust_lb).max()
    df5["roll_low"] = df5["low"].shift(1).rolling(thrust_lb).min()

    # Precompute previous/rolling helpers for signal logic
    df5["p_bbw_prev"] = df5["p_bbw"].shift(1)
    df5["z_min3"] = df5["z50"].rolling(3).min()
    df5["z_max3"] = df5["z50"].rolling(3).max()
    df5["prev_high"] = df5["high"].shift(1)
    df5["prev_low"] = df5["low"].shift(1)
    df5["roll_high3"] = df5["high"].rolling(3).max()
    df5["roll_low3"] = df5["low"].rolling(3).min()
    df5["body"] = (df5["close"] - df5["open"]).abs()
    # Opcional: habilita operações no início do dataset (aquecimento)
    df5["atr14"] = df5["atr14"].bfill()
    df5["tr_med20"] = df5["tr_med20"].bfill()

    # Utility helpers
    def current_position_type():
        if not backtest.positions:
            return None
        return backtest.positions[0].type

    def flat():
        return len(backtest.positions) == 0

    # 4) Backtest loop
    sig_stats = {
        "tot": 0,
        "tradable": 0,
        "reg_long": 0,
        "reg_short": 0,
        "expand": 0,
        "long_ready": 0,
        "short_ready": 0,
        "tp": 0,
        "sl": 0,
    }
    trade_state = None
    long_cd = 0
    short_cd = 0
    for ts, row in df5.iterrows():
        if long_cd > 0:
            long_cd -= 1
        if short_cd > 0:
            short_cd -= 1
        last_candle = pd.Series({
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        }, name=ts)

        operation.backtest_update_candles({symbol: last_candle})

        # Ensure environment has last candle set
        try:
            _row = operation.backtest_symbols_data.loc[symbol]
            _lc = _row.get("last_candle")
            has_last = isinstance(_lc, pd.Series) and (not _lc.empty) and all(k in _lc for k in ("open","high","low","close"))
        except Exception:
            has_last = False
        if not has_last:
            continue

        # Monitor auto-closures (SL/TP/SO) after candle update and only enforce time exit
        pos_now = current_position_type()
        if trade_state is not None:
            # If position was auto-closed by engine, update stats from last deal reason
            if pos_now is None:
                try:
                    last_deal = next(d for d in reversed(backtest.history_deals) if d.symbol == symbol)
                    if last_deal.reason == ENUM_DEAL_REASON.DEAL_REASON_TP:
                        sig_stats["tp"] += 1
                    elif last_deal.reason == ENUM_DEAL_REASON.DEAL_REASON_SL:
                        sig_stats["sl"] += 1
                except StopIteration:
                    pass
                trade_state = None
                continue

            # Still in trade: only time-based exit
            trade_state["bars_in_trade"] = int(trade_state.get("bars_in_trade", 0)) + 1
            if trade_state["bars_in_trade"] >= time_exit_max:
                if pos_now == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
                    operation.close_all_positions(comment=f"ZVIG-{mode}-TIMEEXIT-LONG")
                else:
                    operation.close_all_positions(comment=f"ZVIG-{mode}-TIMEEXIT-SHORT")
                trade_state = None
                continue

        # Volatility floor (absolute, parametrizable)
        atr_floor_pct = ZVIG_ATR_FLOOR
        atr_floor_ok = pd.notna(row.get("atr_pct", np.nan)) and (float(row.get("atr_pct", np.nan)) >= atr_floor_pct)
        if not atr_floor_ok:
            continue

        # Session/day filters removed per request
        sig_stats["tot"] += 1

        tradable_vol = (row.get("p_atr", np.nan) >= atr_min) and (row.get("p_atr", np.nan) <= atr_max)
        if tradable_vol:
            sig_stats["tradable"] += 1
        kama50 = row.get("kama50")
        if np.isnan(kama50):
            continue

        regime_long = (row["close"] > kama50) and (row.get("kama_slope", 0) > 0)
        regime_short = (row["close"] < kama50) and (row.get("kama_slope", 0) < 0)
        if regime_long:
            sig_stats["reg_long"] += 1
        if regime_short:
            sig_stats["reg_short"] += 1

        # Expansion as OR: squeeze-lite OR short-range breakout with body
        expand_a = (row.get("tr", np.nan) >= tr_mul * row.get("tr_med20", np.nan)) and \
                    (row.get("p_bbw_prev", np.nan) <= bbw_prev_max) and \
                    (row.get("p_bbw", np.nan) >= bbw_min)
        rh = row.get("roll_high", np.nan)
        rl = row.get("roll_low", np.nan)
        min_body = body_min_atr
        body_ok = row.get("body", np.nan) >= (min_body * row.get("atr14", np.nan))
        expand_b_long  = (pd.notna(rh) and (row["high"] >= rh) and body_ok)
        expand_b_short = (pd.notna(rl) and (row["low"]  <= rl) and body_ok)
        expand = bool(expand_a or expand_b_long or expand_b_short)
        if expand:
            sig_stats["expand"] += 1

        # Recent z-score extremes (last 3 bars)
        z_min3 = row.get("z_min3", np.nan)
        z_max3 = row.get("z_max3", np.nan)
        z_long_ok = (z_min3 <= -z_abs)
        z_short_ok = (z_max3 >= +z_abs)

        # Thrust via breakout conds above (expand_b_long/short)
        long_thrust = expand_b_long
        short_thrust = expand_b_short

        pos = current_position_type()
        # 3-of-4 objective gates with req_hits
        conds_long  = [regime_long,  z_long_ok,  expand, expand_b_long]
        conds_short = [regime_short, z_short_ok, expand, expand_b_short]

        if sum(bool(c) for c in conds_long) >= req_hits:
            sig_stats["long_ready"] += 1
        if sum(bool(c) for c in conds_short) >= req_hits:
            sig_stats["short_ready"] += 1

        if flat() and (long_cd == 0) and sum(bool(c) for c in conds_long) >= req_hits:
            entry = float(row["close"]) if pd.notna(row.get("close", np.nan)) else None
            atr14 = row.get("atr14", np.nan)
            if np.isnan(atr14):
                atr14 = row.get("tr", np.nan)
            if entry is not None and pd.notna(atr14):
                # Adjust entry for BUY side to include simulated spread (ASK) similar to backtest position_open
                try:
                    tick_size = float(operation.backtest_symbols_data.loc[symbol].tick_size)
                    simulated_spread = int(operation.account_data.simulated_spread)
                except Exception:
                    # Fallbacks in case attributes differ
                    tick_size = float(backtest.backtest_symbols_data.loc[symbol].tick_size) if 'backtest' in locals() else 0.0
                    simulated_spread = int(backtest.account_data.simulated_spread) if 'backtest' in locals() else 0

                entry_adj = entry + (tick_size * simulated_spread)

                risk = 1.2 * float(atr14)
                sl = entry - risk
                tp = entry_adj + 1.6 * risk

                # Enforce minimum SL/TP distances to avoid overtrading and tiny stops
                # Use the larger of: 3 * tick_size or 0.10 * float(atr14) as floor distances
                min_dist = max(3.0 * tick_size, 0.10 * float(atr14))
                sl_ok = abs(entry_adj - sl) >= min_dist
                tp_ok = abs(tp - entry_adj) >= min_dist
                if sl_ok and tp_ok:
                    # Attach SL/TP directly on market entry
                    try:
                        try:
                            lc = operation.backtest_symbols_data.loc[symbol].last_candle
                            if lc is not None:
                                logging.info(
                                    f"[ENTRY PREVIEW] BUY {symbol} last_candle time={getattr(lc, 'name', None)} o={float(lc.get('open')) if 'open' in lc else None} h={float(lc.get('high')) if 'high' in lc else None} l={float(lc.get('low')) if 'low' in lc else None} c={float(lc.get('close')) if 'close' in lc else None}"
                                )
                        except Exception:
                            pass
                        operation.buy(symbol=symbol, volume=1.0, stop_price=sl, profit_price=tp, comment=f"ZVIG-{mode}-LONG")
                    except InsufficientMarginError:
                        break
                else:
                    # Skip entry if SL/TP too tight
                    continue
                trade_state = {
                    "side": "long",
                    "entry": entry_adj,
                    "risk": risk,
                    "sl": sl,
                    "tp": tp,
                    "opened_at": ts,
                    "bars_in_trade": 0,
                }
                long_cd = cooldown_bars
        elif flat() and (short_cd == 0) and sum(bool(c) for c in conds_short) >= req_hits:
            entry = float(row["close"]) if pd.notna(row.get("close", np.nan)) else None
            atr14 = row.get("atr14", np.nan)
            if np.isnan(atr14):
                atr14 = row.get("tr", np.nan)
            if entry is not None and pd.notna(atr14):
                # For SELL side, entry uses BID (close), no spread addition
                try:
                    tick_size = float(operation.backtest_symbols_data.loc[symbol].tick_size)
                    simulated_spread = int(operation.account_data.simulated_spread)
                except Exception:
                    tick_size = float(backtest.backtest_symbols_data.loc[symbol].tick_size) if 'backtest' in locals() else 0.0
                    simulated_spread = int(backtest.account_data.simulated_spread) if 'backtest' in locals() else 0

                entry_adj = entry
                ask_on_entry = entry + (tick_size * simulated_spread)

                risk = 1.2 * float(atr14)
                sl = ask_on_entry + risk
                tp = entry_adj - 1.6 * risk

                # Enforce minimum SL/TP distances
                min_dist = max(3.0 * tick_size, 0.10 * float(atr14))
                sl_ok = abs(entry_adj - sl) >= min_dist
                tp_ok = abs(tp - entry_adj) >= min_dist
                if sl_ok and tp_ok:
                    # Attach SL/TP directly on market entry
                    try:
                        try:
                            lc = operation.backtest_symbols_data.loc[symbol].last_candle
                            if lc is not None:
                                logging.info(
                                    f"[ENTRY PREVIEW] SELL {symbol} last_candle time={getattr(lc, 'name', None)} o={float(lc.get('open')) if 'open' in lc else None} h={float(lc.get('high')) if 'high' in lc else None} l={float(lc.get('low')) if 'low' in lc else None} c={float(lc.get('close')) if 'close' in lc else None}"
                                )
                        except Exception:
                            pass
                        operation.sell(symbol=symbol, volume=1.0, stop_price=sl, profit_price=tp, comment=f"ZVIG-{mode}-SHORT")
                    except InsufficientMarginError:
                        break
                else:
                    # Skip entry if SL/TP too tight
                    continue
                trade_state = {
                    "side": "short",
                    "entry": entry_adj,
                    "risk": risk,
                    "sl": sl,
                    "tp": tp,
                    "opened_at": ts,
                    "bars_in_trade": 0,
                }
                short_cd = cooldown_bars
        else:
            # Optional basic exit: flip on opposite thrust/regime
            if pos == ENUM_POSITION_TYPE.POSITION_TYPE_BUY and (regime_short and short_thrust):
                operation.close_all_positions(comment=f"ZVIG-{mode}-EXIT-LONG")
                trade_state = None
            elif pos == ENUM_POSITION_TYPE.POSITION_TYPE_SELL and (regime_long and long_thrust):
                operation.close_all_positions(comment=f"ZVIG-{mode}-EXIT-SHORT")
                trade_state = None

    # 5) Finalize
    print("\n[ZVIG] Signal gates summary:")
    print(f"Bars: {sig_stats['tot']} | tradable: {sig_stats['tradable']} | expand: {sig_stats['expand']} | regL: {sig_stats['reg_long']} | regS: {sig_stats['reg_short']}")
    print(f"Ready long: {sig_stats['long_ready']} | Ready short: {sig_stats['short_ready']} | TP: {sig_stats['tp']} | SL: {sig_stats['sl']}")
    if backtest.positions:
        operation.close_all_positions(comment="End of backtest - flatten")

    deals = backtest.history_deals or []
    ops_df, _ = build_operations_dataframe(deals)
    stats = compute_statistics(ops_df, backtest=backtest, initial_balance=10_000)

    params = {
        "symbol": symbol,
        "timeframe_name": tf5.name,
        "notes": "Z-VIG baseline without explicit SL/TP automation (pattern-matched to framework).",
    }
    # Enrich report params with run configuration and data coverage
    params.update({
        "mode": mode,
        "atr_min": atr_min,
        "atr_max": atr_max,
        "tr_mul": tr_mul,
        "bbw_prev_max": bbw_prev_max,
        "bbw_min": bbw_min,
        "z_abs": z_abs,
        "body_min_atr": body_min_atr,
        "thrust_lb": thrust_lb,
        "req_hits": req_hits,
        "cooldown_bars": cooldown_bars,
        "time_exit_max": time_exit_max,
        "atr_floor_env": ZVIG_ATR_FLOOR,
        "date_from": str(date_from),
        "date_to": str(date_to),
        "bars_df5": int(len(df5) if df5 is not None else 0),
        "bars_df1h": int(len(df1h) if df1h is not None else 0),
        "df5_start": str(df5.index.min()) if len(df5) else "N/A",
        "df5_end": str(df5.index.max()) if len(df5) else "N/A",
    })

    # Extra sections to include signal gates summary and runtime coverage
    extra_sections = {
        "Signal Gates Summary": "\n".join([
            f"- Total bars scanned: {sig_stats['tot']}",
            f"- Tradable (vol filter pass): {sig_stats['tradable']}",
            f"- Regime long hits: {sig_stats['reg_long']} | Regime short hits: {sig_stats['reg_short']}",
            f"- Expansion hits: {sig_stats['expand']}",
            f"- Ready long (>= req_hits): {sig_stats['long_ready']} | Ready short: {sig_stats['short_ready']}",
            f"- Exits TP: {sig_stats['tp']} | SL: {sig_stats['sl']}",
        ]),
        "Data Coverage (Runtime)": "\n".join([
            f"- DF5 candles: {len(df5)}",
            f"- DF5 interval: {str(df5.index.min()) if len(df5) else 'N/A'} → {str(df5.index.max()) if len(df5) else 'N/A'}",
            f"- DF1H candles: {len(df1h)}",
            f"- DF1H interval: {str(df1h.index.min()) if len(df1h) else 'N/A'} → {str(df1h.index.max()) if len(df1h) else 'N/A'}",
        ]),
    }

    md = render_markdown_report(stats=stats, params=params, extra_sections=extra_sections)
    out_path = save_report_markdown(md, script_file=__file__, symbol=symbol)
    print(f"\nBacktest results saved to: {out_path}")

    # Build operations (entry/exit pairs) from deals and write to Parquet -------------------------
    try:
        # Sort deals chronologically
        sorted_deals = sorted((deals or []), key=lambda d: getattr(d, "time_msc", getattr(d, "time", None)))

        # Group by position_id
        from collections import defaultdict
        deals_by_pos: dict[int, list] = defaultdict(list)
        for d in sorted_deals:
            # Only consider trading deals for the selected symbol
            if getattr(d, "symbol", None) != symbol:
                continue
            deals_by_pos[getattr(d, "position_id", None)].append(d)

        ops_rows = []
        for pos_id, pos_deals in deals_by_pos.items():
            if not pos_id:
                continue
            # Find the first IN as the open deal
            open_deal = next((d for d in pos_deals if getattr(d, "entry", None) == ENUM_DEAL_ENTRY.DEAL_ENTRY_IN), None)
            if open_deal is None:
                continue
            # Any OUT/INOUT correspond to closures for this position id
            for d in pos_deals:
                if getattr(d, "entry", None) in (ENUM_DEAL_ENTRY.DEAL_ENTRY_OUT, ENUM_DEAL_ENTRY.DEAL_ENTRY_INOUT):
                    total_profit = float(getattr(d, "profit", 0) or 0) + float(getattr(d, "swap", 0) or 0) + float(getattr(d, "commission", 0) or 0)
                    # Direction from the opening deal type
                    od_type = getattr(open_deal, "type", None)
                    if od_type == ENUM_DEAL_TYPE.DEAL_TYPE_BUY:
                        direction = "BUY"
                    elif od_type == ENUM_DEAL_TYPE.DEAL_TYPE_SELL:
                        direction = "SELL"
                    else:
                        direction = None
                    ops_rows.append({
                        "position_id": pos_id,
                        "symbol": symbol,
                        "open_time": getattr(open_deal, "time_msc", getattr(open_deal, "time", None)),
                        "close_time": getattr(d, "time_msc", getattr(d, "time", None)),
                        "open_price": float(getattr(open_deal, "price", None)),
                        "close_price": float(getattr(d, "price", None)),
                        "direction": direction,
                        "volume": float(getattr(d, "volume", 0) or 0),
                        "reason": getattr(d, "reason", None),
                        "total_profit": float(total_profit),
                        "comment": getattr(d, "comment", ""),
                    })

        if ops_rows:
            operations_df = pd.DataFrame(ops_rows)
            # Save next to the markdown report, with a clear suffix
            base, _ = os.path.splitext(out_path)
            ops_parquet_path = f"{base}_operations.parquet"
            operations_df.to_parquet(ops_parquet_path, index=False)
            print(f"Operations (entry/exit pairs) saved to: {ops_parquet_path}")
        else:
            print("No entry/exit operation pairs were found to write.")
    except Exception as e:
        print(f"Failed to build or write operations parquet: {e}")

    # Persist backtest account object -------------------------------------------------------------
    try:
        base, _ = os.path.splitext(out_path)
        account_pickle_path = f"{base}_backtest_account.pkl"
        with open(account_pickle_path, "wb") as f:
            pickle.dump(backtest, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"Backtest account object saved to: {account_pickle_path}")
    except Exception as e:
        print(f"Failed to save backtest account object: {e}")

    try:
        base, _ = os.path.splitext(out_path)
        df5_parquet_path = f"{base}_df5.parquet"
        df1h_parquet_path = f"{base}_df1h.parquet"
        if isinstance(df5, pd.DataFrame) and len(df5):
            df5.to_parquet(df5_parquet_path)
            print(f"DF5 saved to: {df5_parquet_path}")
        else:
            print("DF5 is empty or invalid; skipping save.")
        if isinstance(df1h, pd.DataFrame) and len(df1h):
            df1h.to_parquet(df1h_parquet_path)
            print(f"DF1H saved to: {df1h_parquet_path}")
        else:
            print("DF1H is empty or invalid; skipping save.")
    except Exception as e:
        print(f"Failed to save dataframes: {e}")

if __name__ == "__main__":
    main()
