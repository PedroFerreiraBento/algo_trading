from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd
import numpy as np
import logging
import sys
import os
from typing import List, Dict, Any, Optional, Tuple

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
    # VWAP reset by UTC day (robust to naive/tz-aware indexes)
    idx = df.index
    try:
        if isinstance(idx, pd.DatetimeIndex):
            if idx.tz is None:
                day = idx.tz_localize("UTC").date
            else:
                day = idx.tz_convert("UTC").date
        else:
            day = pd.to_datetime(idx).tz_localize("UTC").date
    except Exception:
        day = pd.to_datetime(idx).date
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


def _parkinson_vol(df: pd.DataFrame, window: int = 20) -> pd.Series:
    hl = (np.log(df["high"] / df["low"]).replace([np.inf, -np.inf], np.nan)) ** 2
    return (hl.rolling(window).mean()) / (4.0 * np.log(2.0))


def _rogers_satchell(df: pd.DataFrame, window: int = 20) -> pd.Series:
    ln_hc = np.log(df["high"] / df["close"]).replace([np.inf, -np.inf], np.nan)
    ln_ho = np.log(df["high"] / df["open"]).replace([np.inf, -np.inf], np.nan)
    ln_lc = np.log(df["low"] / df["close"]).replace([np.inf, -np.inf], np.nan)
    ln_lo = np.log(df["low"] / df["open"]).replace([np.inf, -np.inf], np.nan)
    rs = ln_hc * ln_ho + ln_lc * ln_lo
    return rs.rolling(window).mean()


def _augment_bar_features(df5: pd.DataFrame) -> pd.DataFrame:
    df = df5.copy()
    # Ensure baseline indicators exist and are filled
    if "atr14" not in df.columns:
        try:
            df["atr14"] = atr(df, 14)
        except Exception:
            df["atr14"] = true_range(df).rolling(14).mean()
    df["atr14"] = df["atr14"].ffill()
    if "bbw20" not in df.columns:
        try:
            df["bbw20"] = bollinger_bandwidth(df, 20, 2.0)
        except Exception:
            ma = df["close"].rolling(20).mean()
            sd = df["close"].rolling(20).std(ddof=0)
            upper = ma + 2.0 * sd
            lower = ma - 2.0 * sd
            df["bbw20"] = (upper - lower) / df["close"]
    df["bbw20"] = df["bbw20"].ffill()
    df["range"] = df["high"] - df["low"]
    df["body"] = (df["close"] - df["open"]).abs()
    df["marubozu"] = (df["body"] / df["range"]).replace([np.inf, -np.inf], np.nan)
    upper_wick = df["high"] - df[["close", "open"]].max(axis=1)
    lower_wick = df[["close", "open"]].min(axis=1) - df["low"]
    df["wick_asym"] = (upper_wick - lower_wick) / df["range"].replace(0, np.nan)
    # Breakouts for N in {2,3,5}
    df["roll_high_2"] = df["high"].shift(1).rolling(2).max()
    df["roll_low_2"] = df["low"].shift(1).rolling(2).min()
    df["roll_high_3"] = df["high"].shift(1).rolling(3).max()
    df["roll_low_3"] = df["low"].shift(1).rolling(3).min()
    df["roll_high_5"] = df["high"].shift(1).rolling(5).max()
    df["roll_low_5"] = df["low"].shift(1).rolling(5).min()
    df["break_strength3_long"] = (df["close"] - df["roll_high_3"]) / df["atr14"]
    df["break_strength3_short"] = (df["roll_low_3"] - df["close"]) / df["atr14"]
    df["break_strength2_long"] = (df["close"] - df["roll_high_2"]) / df["atr14"]
    df["break_strength2_short"] = (df["roll_low_2"] - df["close"]) / df["atr14"]
    df["break_strength5_long"] = (df["close"] - df["roll_high_5"]) / df["atr14"]
    df["break_strength5_short"] = (df["roll_low_5"] - df["close"]) / df["atr14"]
    df["follow_through_long"] = (df["high"] - df["close"]) / df["atr14"]
    df["follow_through_short"] = (df["close"] - df["low"]) / df["atr14"]
    q25_bbw = df["bbw20"].rolling(500).quantile(0.25)
    df["squeeze_flag"] = (df["bbw20"] < q25_bbw).astype(int)
    df["squeeze_count"] = df["squeeze_flag"].rolling(10).sum()
    inside = (df["high"] <= df["high"].shift(1)) & (df["low"] >= df["low"].shift(1))
    df["inside_ratio"] = inside.rolling(5).mean()
    df["parkinson_vol"] = _parkinson_vol(df, 20)
    df["rs_vol"] = _rogers_satchell(df, 20)
    # Keltner/Bollinger widths and ratio
    atr20 = true_range(df).rolling(20).mean()
    ema20 = df["close"].ewm(span=20, adjust=False).mean()
    kcw = 2.0 * 1.5 * atr20  # absolute width
    sd20 = df["close"].rolling(20).std(ddof=0)
    bbw_abs = 2.0 * 2.0 * sd20
    df["kcw_bbwr"] = (kcw / bbw_abs).replace([np.inf, -np.inf], np.nan)

    # VWAP-related
    vwap_day = session_vwap(df)
    df["dev_vwap"] = df["close"] - vwap_day
    df["z_vol"] = rolling_zscore(df.get("tick_volume", pd.Series(0, index=df.index)).fillna(0), 50)
    df.rename(columns={"z50": "z_vwap"}, inplace=True)
    # q_vwap: percentile rank of dev_vwap/ATR14 (rolling window)
    dev_norm = (df["dev_vwap"] / df["atr14"]).replace([np.inf, -np.inf], np.nan)
    df["q_vwap"] = percentile_rank(dev_norm, window=min(2000, max(400, len(df))))

    # Volume features
    vol = df.get("tick_volume") if "tick_volume" in df.columns else pd.Series(index=df.index, data=np.nan)
    med50 = vol.rolling(50).median()
    df["vol_spike"] = (vol / med50).replace([np.inf, -np.inf], np.nan)
    df["signed_vol20"] = (vol * np.sign(df["close"] - df["open"]))
    df["signed_vol20"] = df["signed_vol20"].rolling(20).sum()
    ret1 = df["close"].pct_change()
    df["corr_pv20"] = ret1.rolling(20).corr(vol)

    # Entropy of normalized returns and Choppiness
    abs_r = ret1.abs()
    def _entropy_window(s: pd.Series) -> float:
        s = s.dropna()
        if len(s) == 0:
            return np.nan
        p = s / s.sum() if s.sum() != 0 else s
        p = p[p > 0]
        return float(-(p * np.log(p)).sum()) if len(p) else np.nan
    df["entropy20"] = abs_r.rolling(20).apply(_entropy_window, raw=False)
    n_chop = 14
    tr_n = true_range(df).rolling(n_chop).sum()
    hh = df["high"].rolling(n_chop).max()
    ll = df["low"].rolling(n_chop).min()
    denom = (hh - ll).replace(0, np.nan)
    df["choppiness14"] = 100.0 * (np.log10(tr_n / denom)) / np.log10(n_chop)
    return df


def _merge_1h_features(df5: pd.DataFrame, df1h: pd.DataFrame) -> pd.DataFrame:
    d1 = df1h.copy()
    d1["atr1h"] = atr(d1, 14)
    d1["mom1h"] = d1["close"].pct_change(3)
    d1_idx = d1.reset_index().rename(columns={"index": "time"})
    d5_idx = df5.reset_index().rename(columns={"index": "time"})
    mg = pd.merge_asof(
        d5_idx.sort_values("time"),
        d1_idx[["time", "kama50", "kama_slope", "atr1h", "mom1h"]].sort_values("time"),
        on="time",
        direction="backward",
    )
    df = df5.copy()
    df["kama50"] = mg["kama50"].values
    df["kama_slope"] = mg["kama_slope"].values
    df["atr1h"] = mg["atr1h"].values
    df["mom1h"] = mg["mom1h"].values
    df["dist_kama1h"] = (df["close"] - df["kama50"]) / df["atr1h"].replace(0, np.nan)
    df["slope1h_norm"] = df["kama_slope"] / df["atr1h"].replace(0, np.nan)
    return df


def _pair_trades(ops_df: pd.DataFrame) -> List[Dict[str, Any]]:
    trades: List[Dict[str, Any]] = []
    stacks: Dict[str, List[Dict[str, Any]]] = {}
    for _, r in ops_df.sort_values("time").iterrows():
        sym = str(r.get("symbol", ""))
        entry = str(r.get("entry", ""))
        t = pd.to_datetime(r.get("time"))
        typ = str(r.get("type", ""))
        price = float(r.get("price", 0.0))
        vol = float(r.get("volume", 0.0))
        comment = str(r.get("comment", ""))
        if entry.endswith("IN") and ("BUY" in typ or typ.endswith("_BUY")):
            stacks.setdefault(sym+":LONG", []).append({"time": t, "price": price, "side": "long", "volume": vol, "comment": comment})
        elif entry.endswith("IN") and ("SELL" in typ or typ.endswith("_SELL")):
            stacks.setdefault(sym+":SHORT", []).append({"time": t, "price": price, "side": "short", "volume": vol, "comment": comment})
        elif entry.endswith("OUT"):
            # MT5 convention: SELL deal closes a LONG; BUY deal closes a SHORT
            key: Optional[str] = None
            if "SELL" in typ:
                key = sym+":LONG"
            elif "BUY" in typ:
                key = sym+":SHORT"
            # Fallback if type is not clear
            if key is None:
                key = sym+":LONG" if stacks.get(sym+":LONG") else sym+":SHORT"
            if key in stacks and stacks[key]:
                ent = stacks[key].pop()
                trades.append({
                    "symbol": sym,
                    "side": ent["side"],
                    "entry_time": ent["time"],
                    "entry_price": float(ent["price"]),
                    "exit_time": t,
                    "exit_price": price,
                    "out_comment": comment,
                })
    return trades


def _build_trade_dataset(df5: pd.DataFrame, trades: List[Dict[str, Any]], ops_df: pd.DataFrame) -> pd.DataFrame:
    # Normalize df5 index to naive UTC for consistent slicing
    df = df5.copy()
    try:
        if isinstance(df.index, pd.DatetimeIndex):
            if df.index.tz is not None:
                df.index = df.index.tz_convert("UTC").tz_localize(None)
            else:
                df.index = pd.to_datetime(df.index).tz_localize(None)
    except Exception:
        pass

    rows: List[Dict[str, Any]] = []
    def _to_naive_utc(ts):
        if pd.isna(ts):
            return pd.NaT
        t = pd.to_datetime(ts)
        try:
            if getattr(t, 'tzinfo', None) is not None or (hasattr(t, 'tz') and t.tz is not None):
                return t.tz_convert('UTC').tz_localize(None)
            else:
                # keep as-is (assume already in the same reference as df index)
                return t.tz_localize(None)
        except Exception:
            try:
                return pd.to_datetime(t).tz_localize(None)
            except Exception:
                return pd.NaT

    for i, tr in enumerate(trades):
        # Normalize trade times to naive (aligned with df index naive UTC above)
        t0 = _to_naive_utc(tr["entry_time"]) if pd.notna(tr["entry_time"]) else pd.NaT
        t1 = _to_naive_utc(tr["exit_time"]) if pd.notna(tr["exit_time"]) else pd.NaT
        side = tr["side"]
        entry = float(tr["entry_price"])
        seg = df.loc[(df.index >= t0) & (df.index <= t1)].copy()
        if seg.empty:
            # Debug alignment once
            try:
                first_idx, last_idx = df.index.min(), df.index.max()
                print(f"[dataset] Empty segment for trade {i} ({side}) {t0}→{t1}. DF range: {first_idx}→{last_idx}")
            except Exception:
                pass
            continue
        atr_entry = float(seg["atr14"].ffill().iloc[0]) if "atr14" in seg.columns else float(seg.iloc[0].get("atr14", np.nan))
        if np.isnan(atr_entry) or atr_entry == 0:
            atr_entry = float(seg.iloc[0].get("tr", np.nan))
        if np.isnan(atr_entry) or atr_entry == 0:
            continue
        R = 1.2 * atr_entry
        if side == "long":
            sl = entry - R
            tp = entry + 1.6 * R
        else:
            sl = entry + R
            tp = entry - 1.6 * R
        tp_R = abs(tp - entry) / R
        sl_R = abs(entry - sl) / R
        asymmetry = tp_R / sl_R if sl_R != 0 else np.nan

        # Trade-level costs (fees+swap) to compute cost_R
        try:
            mask_cost = (ops_df["symbol"].astype(str) == str(tr["symbol"])) & (pd.to_datetime(ops_df["time"]) >= t0) & (pd.to_datetime(ops_df["time"]) <= t1)
            fees = float(ops_df.loc[mask_cost, ["swap", "commission"]].sum().sum())
        except Exception:
            fees = 0.0
        cost_R = (abs(fees) / R) if R else np.nan

        # Precompute constants for the trade
        bbw_entry = float(seg.iloc[0].get("bbw20", np.nan))
        c0 = float(seg.iloc[0].get("close", np.nan))
        kama0 = float(seg.iloc[0].get("kama50", np.nan))
        sign0 = np.sign(c0 - kama0) if (not np.isnan(c0) and not np.isnan(kama0)) else np.nan

        cum_max = -np.inf
        cum_min = np.inf
        prev_mfe = 0.0
        for j, (ts, row) in enumerate(seg.iterrows()):
            c = float(row.get("close", np.nan))
            h = float(row.get("high", np.nan))
            l = float(row.get("low", np.nan))
            if side == "long":
                runup = h - entry
                drawdown = entry - l
                dist_tp_r = (tp - h) / R
                dist_sl_r = (l - sl) / R
            else:
                runup = entry - l
                drawdown = h - entry
                dist_tp_r = (l - tp) / R
                dist_sl_r = (sl - h) / R
            cum_max = max(cum_max, runup)
            cum_min = max(cum_min, drawdown)
            mfe_R = cum_max / R
            mae_R = cum_min / R
            runup_speed = mfe_R - prev_mfe
            prev_mfe = mfe_R
            atr_ratio = (row.get("atr14", np.nan) / atr_entry) if atr_entry else np.nan
            bbw_now = float(row.get("bbw20", np.nan))
            bbw_ratio = (bbw_now / bbw_entry) if (not np.isnan(bbw_entry) and bbw_entry != 0) else np.nan

            # breakeven/trailing flags and trail gap in R (reconstructing strategy logic)
            atr_for_trail = float(row.get("atr14", np.nan))
            if np.isnan(atr_for_trail):
                atr_for_trail = float(row.get("tr", np.nan))
            breakeven_on = runup >= 0.8 * R
            trailing_on = (runup >= 1.2 * R) and (not np.isnan(atr_for_trail))
            if side == "long":
                trail_sl = (c - 1.0 * atr_for_trail) if trailing_on else (entry if breakeven_on else sl)
                trail_gap_R = (c - trail_sl) / R if not np.isnan(c) else np.nan
            else:
                trail_sl = (c + 1.0 * atr_for_trail) if trailing_on else (entry if breakeven_on else sl)
                trail_gap_R = (trail_sl - c) / R if not np.isnan(c) else np.nan

            # Micro regime flip since entry
            sign_now = np.sign(c - float(row.get("kama50", np.nan))) if (not np.isnan(c) and pd.notna(row.get("kama50", np.nan))) else np.nan
            micro_flip = int(sign0 != sign_now) if (pd.notna(sign0) and pd.notna(sign_now)) else np.nan

            # Time normalization and limited one-hot
            H = max(1, len(seg) - 1)
            t_over_H = j / H

            rows.append({
                "trade_id": i,
                "time": ts,
                "symbol": tr["symbol"],
                "side": side,
                "t": j,
                "t_over_H": t_over_H,
                "entry_time": t0,
                "exit_time": t1,
                "entry_price": entry,
                "tp": tp,
                "sl": sl,
                "R": R,
                "tp_R": tp_R,
                "sl_R": sl_R,
                "asymmetry": asymmetry,
                "close": c,
                "high": h,
                "low": l,
                # Core snapshot
                "ATR_pct": row.get("atr_pct", np.nan),
                "p_atr": row.get("p_atr", np.nan),
                "BBW20": row.get("bbw20", np.nan),
                "p_bbw": row.get("p_bbw", np.nan),
                "parkinson_vol": row.get("parkinson_vol", np.nan),
                "rs_vol": row.get("rs_vol", np.nan),
                "marubozu": row.get("marubozu", np.nan),
                "wick_asym": row.get("wick_asym", np.nan),
                "break_strength3": row.get("break_strength3_long", np.nan) if side == "long" else row.get("break_strength3_short", np.nan),
                "break_strength2": row.get("break_strength2_long", np.nan) if side == "long" else row.get("break_strength2_short", np.nan),
                "break_strength5": row.get("break_strength5_long", np.nan) if side == "long" else row.get("break_strength5_short", np.nan),
                "follow_through": row.get("follow_through_long", np.nan) if side == "long" else row.get("follow_through_short", np.nan),
                "squeeze_count": row.get("squeeze_count", np.nan),
                "inside_ratio": row.get("inside_ratio", np.nan),
                "kcw_bbwr": row.get("kcw_bbwr", np.nan),
                "dev_vwap": row.get("dev_vwap", np.nan),
                "z_vwap": row.get("z_vwap", np.nan),
                "q_vwap": row.get("q_vwap", np.nan),
                "dist_kama1h": row.get("dist_kama1h", np.nan),
                "slope1h_norm": row.get("slope1h_norm", np.nan),
                "mom1h": row.get("mom1h", np.nan),
                "vol_ratio": (row.get("atr14", np.nan) / row.get("atr1h", np.nan)) if pd.notna(row.get("atr1h", np.nan)) else np.nan,
                "vol_spike": row.get("vol_spike", np.nan),
                "z_vol": row.get("z_vol", np.nan),
                "signed_vol20": row.get("signed_vol20", np.nan),
                "corr_pv20": row.get("corr_pv20", np.nan),
                # Time features
                "hour": ts.hour if hasattr(ts, "hour") else np.nan,
                "weekday": ts.weekday() if hasattr(ts, "weekday") else np.nan,
                "hour_sin": np.sin((ts.hour % 24) / 24 * 2 * np.pi) if hasattr(ts, "hour") else np.nan,
                "hour_cos": np.cos((ts.hour % 24) / 24 * 2 * np.pi) if hasattr(ts, "hour") else np.nan,
                # AVWAP day distance (normalize by ATR14 as per spec) and side agreement
                "dist_avwap_day": (float(row.get("dev_vwap", np.nan)) / float(row.get("atr14", np.nan))) if (pd.notna(row.get("dev_vwap", np.nan)) and pd.notna(row.get("atr14", np.nan)) and float(row.get("atr14", np.nan)) != 0) else np.nan,
                "side_agreement": (np.sign(c - (c - float(row.get("dev_vwap", np.nan)))) * (1 if side == "long" else -1)) if pd.notna(row.get("dev_vwap", np.nan)) else np.nan,
                # Dynamics
                "mfe_R": mfe_R,
                "mae_R": mae_R,
                "dist_TP_R": dist_tp_r,
                "dist_SL_R": dist_sl_r,
                "runup_speed": runup_speed,
                "drawdown_speed": (mae_R - (rows[-1]["mae_R"] if (len(rows) > 0 and rows[-1]["trade_id"] == i) else 0.0)),
                "accel": (runup_speed - (rows[-1]["runup_speed"] if (len(rows) > 0 and rows[-1]["trade_id"] == i) else 0.0)),
                "atr_ratio": atr_ratio,
                "bbw_ratio": bbw_ratio,
                # Stop state reconstruction and cost
                "breakeven_on": int(breakeven_on),
                "trailing_on": int(trailing_on),
                "trail_gap_R": trail_gap_R,
                "cost_R": cost_R,
                # Regime flip
                "micro_flip": micro_flip,
                "outcome": tr.get("out_comment", ""),
            })

            # Limited one-hot for t (1..40)
            max_onehot = 40
            onehot_idx = min(j+1, max_onehot)
            for k in range(1, max_onehot+1):
                rows[-1][f"t_is_{k}"] = 1 if onehot_idx == k else 0

            # Weekday one-hot (0..6)
            wd = rows[-1]["weekday"]
            for k in range(7):
                rows[-1][f"weekday_{k}"] = 1 if wd == k else 0

            # Session flags (approximate UTC blocks)
            hr = rows[-1]["hour"]
            session_london = int(7 <= hr <= 16) if pd.notna(hr) else 0
            session_ny = int(12 <= hr <= 21) if pd.notna(hr) else 0
            session_overlap = int(12 <= hr <= 16) if pd.notna(hr) else 0
            rows[-1]["session_london"] = session_london
            rows[-1]["session_ny"] = session_ny
            rows[-1]["session_overlap"] = session_overlap
    return pd.DataFrame(rows)


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
    mode = os.getenv("ZVIG_MODE", "TURBO").upper()
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
    df5["atr14"] = df5["atr14"].fillna(method="bfill")
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
        try:
            operation.backtest_symbols_data.at[symbol, "last_candle"] = last_candle
        except Exception:
            pass

        # Ensure environment has last candle set
        try:
            _row = operation.backtest_symbols_data.loc[symbol]
            _lc = _row.get("last_candle")
            has_last = isinstance(_lc, pd.Series) and (not _lc.empty) and all(k in _lc for k in ("open","high","low","close"))
        except Exception:
            has_last = False
        if not has_last:
            continue

        # SL/TP check for open positions
        pos_now = current_position_type()
        if trade_state is not None and pos_now is not None:
            trade_state["bars_in_trade"] = int(trade_state.get("bars_in_trade", 0)) + 1
            # Pre-check dynamic risk management: breakeven and ATR trailing
            try:
                atr_for_trail = row.get("atr14", np.nan)
                if np.isnan(atr_for_trail):
                    atr_for_trail = row.get("tr", np.nan)
            except Exception:
                atr_for_trail = row.get("atr14", np.nan)
            if pos_now == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
                up = float(row.get("high", np.nan)) - float(trade_state["entry"])
                if pd.notna(up):
                    if up >= 0.8 * float(trade_state["risk"]):
                        trade_state["sl"] = max(float(trade_state["sl"]), float(trade_state["entry"]))
                    if (up >= 1.2 * float(trade_state["risk"])) and pd.notna(atr_for_trail):
                        trail_sl = float(row.get("close", np.nan)) - 1.0 * float(atr_for_trail)
                        if pd.notna(trail_sl):
                            trade_state["sl"] = max(float(trade_state["sl"]), trail_sl)
            elif pos_now == ENUM_POSITION_TYPE.POSITION_TYPE_SELL:
                down = float(trade_state["entry"]) - float(row.get("low", np.nan))
                if pd.notna(down):
                    if down >= 0.8 * float(trade_state["risk"]):
                        trade_state["sl"] = min(float(trade_state["sl"]), float(trade_state["entry"]))
                    if (down >= 1.2 * float(trade_state["risk"])) and pd.notna(atr_for_trail):
                        trail_sl = float(row.get("close", np.nan)) + 1.0 * float(atr_for_trail)
                        if pd.notna(trail_sl):
                            trade_state["sl"] = min(float(trade_state["sl"]), trail_sl)
            if pos_now == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
                if row["low"] <= trade_state["sl"]:
                    operation.close_all_positions(comment="ZVIGL-SL")
                    sig_stats["sl"] += 1
                    trade_state = None
                    continue
                elif row["high"] >= trade_state["tp"]:
                    operation.close_all_positions(comment="ZVIGL-TP")
                    sig_stats["tp"] += 1
                    trade_state = None
                    continue
                elif trade_state["bars_in_trade"] >= time_exit_max:
                    operation.close_all_positions(comment=f"ZVIG-{mode}-TIMEEXIT-LONG")
                    trade_state = None
                    continue
            elif pos_now == ENUM_POSITION_TYPE.POSITION_TYPE_SELL:
                if row["high"] >= trade_state["sl"]:
                    operation.close_all_positions(comment="ZVIGL-SL")
                    sig_stats["sl"] += 1
                    trade_state = None
                    continue
                elif row["low"] <= trade_state["tp"]:
                    operation.close_all_positions(comment="ZVIGL-TP")
                    sig_stats["tp"] += 1
                    trade_state = None
                    continue
                elif trade_state["bars_in_trade"] >= time_exit_max:
                    operation.close_all_positions(comment=f"ZVIG-{mode}-TIMEEXIT-SHORT")
                    trade_state = None
                    continue

        # Volatility floor (absolute, parametrizable). Disabled in TURBO mode to avoid over-filtering.
        if mode != "TURBO":
            atr_floor_pct = float(os.getenv("ZVIG_ATR_FLOOR", "0.00035"))
            atr_floor_ok = pd.notna(row.get("atr_pct", np.nan)) and (float(row.get("atr_pct", np.nan)) >= atr_floor_pct)
            if not atr_floor_ok:
                continue

        # Session/day filters removed per request

        # Filters (TURBO não bloqueia por volatilidade)
        sig_stats["tot"] += 1
        if mode == "TURBO":
            tradable_vol = True
        else:
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
        if mode == "MEDIUM":
            expand_a = (row.get("tr", np.nan) >= tr_mul * row.get("tr_med20", np.nan)) and \
                       (row.get("p_bbw_prev", np.nan) <= 0.30) and \
                       (row.get("p_bbw", np.nan) >= 0.50) and \
                       ((row.get("close", np.nan) - row.get("open", np.nan)).__abs__() >= (0.25 * row.get("atr14", np.nan)))
        else:
            expand_a = (row.get("tr", np.nan) >= tr_mul * row.get("tr_med20", np.nan)) and \
                       (row.get("p_bbw_prev", np.nan) <= bbw_prev_max) and \
                       (row.get("p_bbw", np.nan) >= bbw_min)
        rh = row.get("roll_high", np.nan)
        rl = row.get("roll_low", np.nan)
        min_body = body_min_atr if mode != "TURBO" else 0.0
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
                risk = 1.2 * float(atr14)
                sl = entry - risk
                tp = entry + 1.6 * risk
                # Attach SL/TP directly on market entry
                operation.buy(symbol=symbol, volume=1.0, stop_price=sl, profit_price=tp, comment=f"ZVIG-{mode}-LONG")
                trade_state = {
                    "side": "long",
                    "entry": entry,
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
                risk = 1.2 * float(atr14)
                sl = entry + risk
                tp = entry - 1.6 * risk
                # Attach SL/TP directly on market entry
                operation.sell(symbol=symbol, volume=1.0, stop_price=sl, profit_price=tp, comment=f"ZVIG-{mode}-SHORT")
                trade_state = {
                    "side": "short",
                    "entry": entry,
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
    # Debug: quick summary of deals
    try:
        print("[dataset] deals count:", len(deals))
        if not ops_df.empty:
            vc_entry = ops_df["entry"].astype(str).value_counts(dropna=False)
            vc_type = ops_df["type"].astype(str).value_counts(dropna=False)
            print("[dataset] ops entry counts:\n", vc_entry.to_string())
            print("[dataset] ops type counts:\n", vc_type.to_string())
        else:
            print("[dataset] ops_df is empty after build_operations_dataframe")
    except Exception:
        pass
    stats = compute_statistics(ops_df, backtest=backtest, initial_balance=10_000)

    # Build per-trade, per-bar dataset for signal validator
    try:
        df5_aug = _augment_bar_features(_merge_1h_features(df5, df1h))
        trades = _pair_trades(ops_df)
        print(f"[dataset] Paired trades: {len(trades)}")
        trade_ds = _build_trade_dataset(df5_aug, trades, ops_df)
        print(f"[dataset] Rows built: {len(trade_ds)}")
    except Exception as e:
        print(f"[dataset] Failed to build dataset: {e}")
        trade_ds = pd.DataFrame()

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
        "atr_floor_env": os.getenv("ZVIG_ATR_FLOOR", "not_set"),
        "date_from": str(date_from),
        "date_to": str(date_to),
        "allow_hours": "{1,2,11,15,17,23}",
        "allow_days": "{3,4}",
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

    # Save dataset files next to script
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ts_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"signal_dataset_{symbol}_{ts_tag}"
        csv_path = os.path.join(script_dir, base + ".csv")
        pq_path = os.path.join(script_dir, base + ".parquet")
        # Also save raw ops_df for troubleshooting pairing/time alignment
        try:
            ops_csv = os.path.join(script_dir, f"ops_{symbol}_{ts_tag}.csv")
            (ops_df if ops_df is not None else pd.DataFrame()).to_csv(ops_csv, index=False)
            print(f"[dataset] Ops dataframe saved to: {ops_csv}")
        except Exception as e:
            print(f"[dataset] Failed to save ops_df: {e}")
        # Always save CSV (even if empty) for inspection
        (trade_ds if trade_ds is not None else pd.DataFrame()).to_csv(csv_path, index=False)
        print(f"Signal dataset (CSV) saved to: {csv_path}")
        # Try Parquet with available engine
        try:
            engine = None
            try:
                import pyarrow  # type: ignore
                engine = "pyarrow"
            except Exception:
                try:
                    import fastparquet  # type: ignore
                    engine = "fastparquet"
                except Exception:
                    engine = None
            if engine:
                (trade_ds if trade_ds is not None else pd.DataFrame()).to_parquet(pq_path, index=False, engine=engine)
                print(f"Signal dataset (Parquet) saved to: {pq_path} (engine={engine})")
            else:
                print("[dataset] Parquet engine not available (install pyarrow or fastparquet). Skipped Parquet save.")
        except Exception as e:
            print(f"[dataset] Parquet save failed: {e}")
    except Exception as e:
        print(f"[dataset] Save failed: {e}")


if __name__ == "__main__":
    main()
