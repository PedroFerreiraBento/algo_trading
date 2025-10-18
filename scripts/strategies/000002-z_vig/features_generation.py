from __future__ import annotations

import os
import json
import math
from datetime import timezone
import numpy as np
import pandas as pd

PREV_CANDLES: int = int(os.getenv("ZVIG_PREV_CANDLES", "50"))


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
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("Expected DatetimeIndex for VWAP calculation")
    if df.index.tz is None:
        df = df.tz_localize("UTC")
    else:
        df = df.tz_convert("UTC")
    day = df.index.tz_convert(timezone.utc).date
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    vol = df.get("tick_volume", pd.Series(1.0, index=df.index))
    cum_tp_vol = tp.groupby(day).apply(lambda s: s.cumsum())
    cum_vol = vol.groupby(day).apply(lambda s: s.cumsum())
    cum_tp_vol.index = df.index
    cum_vol.index = df.index
    out = cum_tp_vol / cum_vol.replace(0, np.nan)
    return out


def percentile_rank(series: pd.Series, window: int) -> pd.Series:
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
    change = series.diff(length).abs()
    volatility = series.diff().abs().rolling(length).sum()
    er = change / volatility.replace(0, np.nan)
    sc = (er * (2 / (fast + 1) - 2 / (slow + 1)) + 2 / (slow + 1)) ** 2
    kama_vals = [np.nan] * len(series)
    if len(series) > 0:
        kama_vals[length - 1] = series.iloc[length - 1]
    for i in range(length, len(series)):
        prev = kama_vals[i - 1] if not math.isnan(kama_vals[i - 1]) else series.iloc[i - 1]
        kama_vals[i] = prev + sc.iloc[i] * (series.iloc[i] - prev)
    return pd.Series(kama_vals, index=series.index)


def compute_features(df5: pd.DataFrame, df1h: pd.DataFrame) -> pd.DataFrame:
    df5 = df5.copy()
    if not isinstance(df5.index, pd.DatetimeIndex):
        if "time" in df5.columns:
            df5["time"] = pd.to_datetime(df5["time"], utc=True, errors="coerce")
            df5 = df5.set_index("time")
        else:
            raise ValueError("df5 must have DatetimeIndex or a 'time' column")
    if df5.index.tz is None:
        df5.index = df5.index.tz_localize("UTC")

    df1h = df1h.copy()
    if not isinstance(df1h.index, pd.DatetimeIndex):
        if "time" in df1h.columns:
            df1h["time"] = pd.to_datetime(df1h["time"], utc=True, errors="coerce")
            df1h = df1h.set_index("time")
        else:
            raise ValueError("df1h must have DatetimeIndex or a 'time' column")
    if df1h.index.tz is None:
        df1h.index = df1h.index.tz_localize("UTC")

    df5["atr14"] = atr(df5, 14)
    df5["atr_pct"] = df5["atr14"] / df5["close"]
    df5["bbw20"] = bollinger_bandwidth(df5, 20, 2.0)
    df5["tr"] = true_range(df5)
    df5["tr_med20"] = df5["tr"].rolling(20).median()

    vwap_sess = session_vwap(df5)
    dev = df5["close"] - vwap_sess
    df5["z50"] = rolling_zscore(dev, 50)

    win_bbw = min(720, len(df5))
    win_atr = min(2000, len(df5))
    df5["p_bbw"] = percentile_rank(df5["bbw20"], window=max(win_bbw, 200))
    df5["p_atr"] = percentile_rank(df5["atr_pct"], window=max(win_atr, 400))

    df5["p_bbw"] = df5["p_bbw"].fillna(0.5)
    df5["p_atr"] = df5["p_atr"].fillna(0.5)

    df1h["kama50"] = kama(df1h["close"], 50)
    df1h["kama_slope"] = df1h["kama50"].diff(5)

    # Align 1h features to 5m, robust to schema variations
    try:
        df1h_idx = df1h.reset_index().rename(columns={"index": "time"})
        df5_idx = df5.reset_index().rename(columns={"index": "time"})
        merged = pd.merge_asof(
            df5_idx.sort_values("time"),
            df1h_idx[["time", "kama50", "kama_slope"]].sort_values("time"),
            on="time",
            direction="backward",
        )
        if "kama50" in merged.columns and "kama_slope" in merged.columns:
            df5["kama50"] = merged["kama50"].values
            df5["kama_slope"] = merged["kama_slope"].values
        else:
            raise KeyError("kama columns missing after merge_asof")
    except Exception:
        # Fallback: forward-fill 1h indicators onto 5m index
        df5["kama50"] = df1h["kama50"].reindex(df5.index, method="ffill")
        df5["kama_slope"] = df1h["kama_slope"].reindex(df5.index, method="ffill")
    df5["kama50"] = df5["kama50"].fillna(df5["close"].rolling(60).mean())
    df5["kama50"] = df5["kama50"].bfill()

    thrust_lb = 2
    df5["roll_high"] = df5["high"].shift(1).rolling(thrust_lb).max()
    df5["roll_low"] = df5["low"].shift(1).rolling(thrust_lb).min()

    df5["p_bbw_prev"] = df5["p_bbw"].shift(1)
    df5["z_min3"] = df5["z50"].rolling(3).min()
    df5["z_max3"] = df5["z50"].rolling(3).max()
    df5["prev_high"] = df5["high"].shift(1)
    df5["prev_low"] = df5["low"].shift(1)
    df5["roll_high3"] = df5["high"].rolling(3).max()
    df5["roll_low3"] = df5["low"].rolling(3).min()
    df5["body"] = (df5["close"] - df5["open"]).abs()

    df5["atr14"] = df5["atr14"].bfill()
    df5["tr_med20"] = df5["tr_med20"].bfill()

    return df5


def attach_context_candles(ops: pd.DataFrame, df5: pd.DataFrame, n_prev: int) -> pd.DataFrame:
    ops = ops.copy()
    if "open_time" in ops.columns:
        from pandas.api.types import is_integer_dtype, is_datetime64_any_dtype
        col = ops["open_time"]
        if is_integer_dtype(col):
            ops["open_time"] = pd.to_datetime(col, unit="ms", utc=True, errors="coerce")
        elif is_datetime64_any_dtype(col):
            # Ensure UTC tz
            if getattr(col.dt, "tz", None) is None:
                ops["open_time"] = col.dt.tz_localize("UTC")
            else:
                ops["open_time"] = col.dt.tz_convert("UTC")
        else:
            ops["open_time"] = pd.to_datetime(col, utc=True, errors="coerce")
    else:
        raise ValueError("operations parquet must contain 'open_time'")

    if not isinstance(df5.index, pd.DatetimeIndex):
        raise ValueError("df5 must use a DatetimeIndex")

    def build_window(ts: pd.Timestamp) -> str:
        if pd.isna(ts):
            return json.dumps([])
        idx = df5.index.searchsorted(ts, side="right") - 1
        if idx < 0:
            return json.dumps([])
        end = idx
        start = max(0, end - n_prev)
        window = df5.iloc[start : end + 1]
        # Prepare JSON-serializable records with all columns + ISO time
        win = window.copy()
        win = win.reset_index().rename(columns={"index": "time"})
        # Ensure ISO 8601 UTC time strings
        from pandas.api.types import is_datetime64_any_dtype
        if isinstance(win["time"].dtype, pd.DatetimeTZDtype):
            win["time"] = win["time"].dt.tz_convert("UTC").map(lambda x: x.isoformat())
        elif is_datetime64_any_dtype(win["time"]):
            win["time"] = win["time"].dt.tz_localize("UTC").map(lambda x: x.isoformat())
        else:
            t = pd.to_datetime(win["time"], utc=True, errors="coerce")
            win["time"] = t.map(lambda x: x.isoformat() if not pd.isna(x) else None)

        def to_py(v):
            if pd.isna(v):
                return None
            if isinstance(v, (np.floating,)):
                return float(v)
            if isinstance(v, (np.integer,)):
                return int(v)
            if isinstance(v, (np.bool_, bool)):
                return bool(v)
            return v

        records = []
        for rec in win.to_dict(orient="records"):
            records.append({k: to_py(v) for k, v in rec.items()})
        return json.dumps(records)

    ops["context_candles_json"] = ops["open_time"].apply(build_window)
    return ops


def main():
    base_dir = os.path.dirname(__file__)
    df5_path = os.path.join(base_dir, "backtest_results_EURUSD_df5.parquet")
    df1h_path = os.path.join(base_dir, "backtest_results_EURUSD_df1h.parquet")
    ops_path = os.path.join(base_dir, "backtest_results_EURUSD_operations.parquet")

    df5 = pd.read_parquet(df5_path)
    df1h = pd.read_parquet(df1h_path)

    if "time" in df5.columns and not isinstance(df5.index, pd.DatetimeIndex):
        df5["time"] = pd.to_datetime(df5["time"], utc=True, errors="coerce")
        df5 = df5.set_index("time")
    if df5.index.tz is None:
        df5.index = df5.index.tz_localize("UTC")

    if "time" in df1h.columns and not isinstance(df1h.index, pd.DatetimeIndex):
        df1h["time"] = pd.to_datetime(df1h["time"], utc=True, errors="coerce")
        df1h = df1h.set_index("time")
    if df1h.index.tz is None:
        df1h.index = df1h.index.tz_localize("UTC")

    df5_feat = compute_features(df5, df1h)
    df5_feat.to_parquet(df5_path)

    ops = pd.read_parquet(ops_path)
    ops_ctx = attach_context_candles(ops, df5_feat, PREV_CANDLES)
    ops_ctx.to_parquet(ops_path, index=False)


if __name__ == "__main__":
    main()
