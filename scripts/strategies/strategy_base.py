from __future__ import annotations

from typing import Dict, Any, Tuple, Optional, List
import os
from datetime import datetime
from dataclasses import dataclass
import pandas as pd

from algo_trading.sources.MetaTrader5_source.account.account import Account
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_DEAL_ENTRY,
    ENUM_DEAL_TYPE,
)


# ===== Shared Credentials =====
@dataclass(frozen=True)
class Credentials:
    login: int
    server: str
    password: str
    path: str = ""


# Default demo credentials (used by templates/examples)
DEFAULT_CREDENTIALS = Credentials(
    login=5041151393,
    server="MetaQuotes-Demo",
    password="V*Fo2qVq",
    path="",
)


# ===== Session / Login Utilities =====
def login_live_and_backtest(*, login: int, server: str, password: str, path: str = "", balance: float = 10_000, leverage: int = 100):
    """Login to live (to enable data access) and create a backtest environment.
    Returns (account, backtest, operation).
    """
    account = Account()
    account.login_live(login=login, server=server, password=password, path=path)
    backtest = account.login_backtest(balance=balance, leverage=leverage)
    return account, backtest, backtest.operation


# ===== Deals -> DataFrame =====
def build_operations_dataframe(deals: List[Any]) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Builds operations DataFrame from deals and returns (ops_df, costs_summary).
    Excludes initial deposits/balance adjustments from ops.
    """
    rows: List[Dict[str, Any]] = []
    initial_deposit_seen = False

    for d in deals or []:
        # Safe enum conversion fallback to raw value
        try:
            entry_name = ENUM_DEAL_ENTRY(d.entry).name if hasattr(d, "entry") else "N/A"
            type_name = ENUM_DEAL_TYPE(d.type).name
        except Exception:
            entry_name = str(getattr(d, "entry", "N/A"))
            type_name = str(getattr(d, "type", "N/A"))

        # Skip first BALANCE ENTRY_IN as initial deposit
        if not initial_deposit_seen and type_name == "DEAL_TYPE_BALANCE" and entry_name == "DEAL_ENTRY_IN":
            initial_deposit_seen = True
            continue

        swap = float(getattr(d, "swap", 0) or 0)
        commission = float(getattr(d, "commission", 0) or 0)
        profit = float(getattr(d, "profit", 0) or 0)
        total_profit = profit + swap + commission

        rows.append(
            {
                "time": getattr(d, "time", None),
                "ticket": getattr(d, "ticket", None),
                "symbol": getattr(d, "symbol", None),
                "type": type_name,
                "entry": entry_name,
                "volume": float(getattr(d, "volume", 0) or 0),
                "price": float(getattr(d, "price", 0) or 0),
                "profit": profit,
                "swap": swap,
                "commission": commission,
                "total_profit": total_profit,
                "comment": getattr(d, "comment", "") or "",
            }
        )

    if not rows:
        ops_df = pd.DataFrame(columns=["time", "ticket", "symbol", "type", "entry", "volume", "price", "profit", "swap", "commission", "total_profit", "comment"])  # noqa: E501
    else:
        ops_df = pd.DataFrame(rows)
        # Sort and filter out balance/credit operations from stats
        ops_df = ops_df.sort_values("time")
        ops_df["profit"] = pd.to_numeric(ops_df["profit"], errors="coerce").fillna(0)
        ops_df["swap"] = pd.to_numeric(ops_df["swap"], errors="coerce").fillna(0)
        ops_df["commission"] = pd.to_numeric(ops_df["commission"], errors="coerce").fillna(0)
        ops_df["total_profit"] = ops_df["profit"] + ops_df["swap"] + ops_df["commission"]
        # Filter only true trading operations (ignore balance/credit)
        mask = ~ops_df["type"].isin(["DEAL_BALANCE", "DEAL_TYPE_BALANCE", "DEAL_CREDIT", "DEAL_TYPE_CREDIT", "DEAL_TYPE_CHARGE"])  # noqa: E501
        ops_df = ops_df[mask].copy()

    costs_summary = {
        "total_swap": float(ops_df["swap"].sum()) if not ops_df.empty else 0.0,
        "total_commission": float(ops_df["commission"].sum()) if not ops_df.empty else 0.0,
    }
    return ops_df, costs_summary


# ===== Statistics =====
def compute_statistics(ops_df: pd.DataFrame, *, backtest: Any, initial_balance: float) -> Dict[str, Any]:
    """Computes a comprehensive set of statistics from ops_df and backtest state."""
    stats: Dict[str, Any] = {}

    # Consider only closed trades (exits) for trade statistics and counts
    closed_mask = ops_df.get("entry").astype(str).str.endswith("OUT") if "entry" in ops_df.columns else pd.Series(False, index=ops_df.index)
    closed_df = ops_df[closed_mask].copy()
    df_stats = closed_df
    total_ops = len(df_stats)
    stats["total_ops"] = total_ops

    if total_ops > 0:
        stats["total_pnl"] = float(df_stats["total_profit"].sum())
        stats["avg_pnl"] = float(df_stats["total_profit"].mean())
        stats["wins"] = int((df_stats["total_profit"] > 0).sum())
        stats["losses"] = int((df_stats["total_profit"] < 0).sum())
        stats["win_rate"] = (stats["wins"] / total_ops) * 100.0 if total_ops else 0.0

        trade_profits = df_stats["total_profit"].copy()
        if len(trade_profits) > 0:
            q_low = float(trade_profits.quantile(0.01))
            q_high = float(trade_profits.quantile(0.99))
            filtered = trade_profits[(trade_profits >= q_low) & (trade_profits <= q_high)]
            if len(filtered) > 0:
                stats["best_trade"] = float(filtered.max())
                stats["worst_trade"] = float(filtered.min())
            else:
                stats["best_trade"] = float(trade_profits.max())
                stats["worst_trade"] = float(trade_profits.min())
        else:
            stats["best_trade"] = 0.0
            stats["worst_trade"] = 0.0

        # Costs
        stats["total_swap"] = float(df_stats["swap"].sum())
        stats["total_commission"] = float(df_stats["commission"].sum())

        # Equity curve including costs (profit + swap + commission)
        equity_curve = initial_balance + df_stats["total_profit"].cumsum()
        stats["equity_curve"] = equity_curve
        rolling_max = equity_curve.cummax()
        drawdown = equity_curve - rolling_max
        stats["max_drawdown"] = float(drawdown.min()) if len(drawdown) else 0.0
        stats["max_dd_pct"] = (stats["max_drawdown"] / float(rolling_max.max()) * 100.0) if float(rolling_max.max() or 0) else 0.0

        # Derived risk metrics
        wins = stats["wins"]
        losses = stats["losses"]
        avg_win = float(df_stats[df_stats["total_profit"] > 0]["total_profit"].mean()) if wins > 0 else 0.0
        avg_loss = float(abs(df_stats[df_stats["total_profit"] < 0]["total_profit"].mean())) if losses > 0 else 0.0
        stats["avg_win"], stats["avg_loss"] = avg_win, avg_loss
        stats["win_loss_ratio"] = (avg_win / avg_loss) if avg_loss != 0 else float("inf")

        gross_profit = float(df_stats[df_stats["total_profit"] > 0]["total_profit"].sum())
        gross_loss = float(abs(df_stats[df_stats["total_profit"] < 0]["total_profit"].sum()))
        stats["profit_factor"] = (gross_profit / gross_loss) if gross_loss != 0 else float("inf")

        stats["risk_reward_ratio"] = (avg_win / avg_loss) if avg_loss != 0 else float("inf")
        stats["expectancy"] = (stats["win_rate"]/100.0 * avg_win) - ((100.0 - stats["win_rate"]) / 100.0 * avg_loss)

        returns_std = float(df_stats["total_profit"].std() or 0)
        stats["returns_std"] = returns_std
        stats["sharpe_ratio"] = (stats["avg_pnl"] / returns_std) if returns_std != 0 else 0.0

        final_balance = float(getattr(backtest, "balance", initial_balance))
        stats["initial_balance"] = float(initial_balance)
        stats["final_balance"] = final_balance
        stats["actual_total_pnl"] = final_balance - float(initial_balance)
        stats["recovery_factor"] = (stats["actual_total_pnl"] / abs(stats["max_drawdown"])) if stats["max_drawdown"] != 0 else float("inf")

        # Optional time-based stats
        if "time" in df_stats.columns and len(df_stats) > 1:
            ops_df = df_stats.copy()
            ops_df["time"] = pd.to_datetime(ops_df["time"])  # ensure dtype
            trade_duration_days = (ops_df["time"].max() - ops_df["time"].min()).days
            stats["avg_trade_duration_days"] = trade_duration_days / len(ops_df) if len(ops_df) else 0

            # Helpers to count candles between two timestamps
            def _count_bars_between(bt: Any, start: pd.Timestamp, end: pd.Timestamp) -> Optional[int]:
                candidates = [
                    getattr(bt, "bars_df", None),
                    getattr(bt, "price_df", None),
                    getattr(bt, "candles_df", None),
                    getattr(bt, "history", None),
                    getattr(bt, "data", None),
                    getattr(getattr(bt, "market", None), "bars_df", None),
                ]
                for df in candidates:
                    if df is None:
                        continue
                    try:
                        if hasattr(df, "index") and isinstance(df.index, pd.DatetimeIndex):
                            return int(df.loc[(df.index >= start) & (df.index <= end)].shape[0])
                        if isinstance(df, pd.DataFrame) and "time" in df.columns:
                            dd = df.copy()
                            dd["time"] = pd.to_datetime(dd["time"])  # ensure
                            return int(dd[(dd["time"] >= start) & (dd["time"] <= end)].shape[0])
                    except Exception:
                        continue
                return None

            # Per-trade duration estimation using ENTRY_IN/ENTRY_OUT pairing per symbol (in candles)
            durations_bars: List[int] = []
            stacks: Dict[str, List[pd.Timestamp]] = {}
            for _, row in ops_df.sort_values("time").iterrows():
                sym = str(row.get("symbol", ""))
                entry = str(row.get("entry", ""))
                t = row["time"]
                if entry.endswith("IN"):
                    stacks.setdefault(sym, []).append(t)
                elif entry.endswith("OUT"):
                    if sym in stacks and stacks[sym]:
                        t_in = stacks[sym].pop()
                        cnt = _count_bars_between(backtest, t_in, t)
                        if cnt is not None:
                            durations_bars.append(int(cnt))

            if durations_bars:
                s = pd.Series(durations_bars, dtype="int64")
                stats["trade_duration_candles_summary"] = {
                    "min": int(s.min()),
                    "max": int(s.max()),
                    "mean": float(s.mean()),
                    "median": float(s.median()),
                    "p10": float(s.quantile(0.10)),
                    "p25": float(s.quantile(0.25)),
                    "p50": float(s.quantile(0.50)),
                    "p75": float(s.quantile(0.75)),
                    "p90": float(s.quantile(0.90)),
                }
            else:
                stats["trade_duration_candles_summary"] = None

            # Inter-trade gap (between consecutive exits) in candles
            times = ops_df.sort_values("time")["time"].to_list()
            gaps_bars: List[int] = []
            for i in range(1, len(times)):
                cnt = _count_bars_between(backtest, times[i-1], times[i])
                if cnt is not None:
                    gaps_bars.append(int(cnt))
            if gaps_bars:
                g = pd.Series(gaps_bars, dtype="int64")
                stats["inter_trade_gap_candles_summary"] = {
                    "min": int(g.min()),
                    "max": int(g.max()),
                    "mean": float(g.mean()),
                    "median": float(g.median()),
                    "p10": float(g.quantile(0.10)),
                    "p25": float(g.quantile(0.25)),
                    "p50": float(g.quantile(0.50)),
                    "p75": float(g.quantile(0.75)),
                    "p90": float(g.quantile(0.90)),
                }
            else:
                stats["inter_trade_gap_candles_summary"] = None

            # Signals by weekday and hour of day
            ops_df["weekday"] = ops_df["time"].dt.weekday
            ops_df["hour"] = ops_df["time"].dt.hour
            stats["ops_by_weekday"] = {int(k): int(v) for k, v in ops_df["weekday"].value_counts().sort_index().to_dict().items()}
            stats["ops_by_hour"] = {int(k): int(v) for k, v in ops_df["hour"].value_counts().sort_index().to_dict().items()}

            # Period statistics (weekday and hour)
            def _agg_trade_stats(df: pd.DataFrame) -> Dict[str, Any]:
                n = len(df)
                if n == 0:
                    return {
                        "count": 0,
                        "wins": 0,
                        "losses": 0,
                        "win_rate": 0.0,
                        "best_trade": 0.0,
                        "worst_trade": 0.0,
                        "avg_win": 0.0,
                        "avg_loss": 0.0,
                        "profit_factor": float("inf"),
                        "expectancy": 0.0,
                        "total_pnl": 0.0,
                        "avg_pnl": 0.0,
                    }
                total_profit = df["total_profit"]
                wins_mask = total_profit > 0
                losses_mask = total_profit < 0
                wins_c = int(wins_mask.sum())
                losses_c = int(losses_mask.sum())
                win_rate = (wins_c / n) * 100.0 if n else 0.0
                best_trade = float(total_profit.max()) if n else 0.0
                worst_trade = float(total_profit.min()) if n else 0.0
                avg_win = float(df[wins_mask]["total_profit"].mean()) if wins_c > 0 else 0.0
                avg_loss = float(abs(df[losses_mask]["total_profit"].mean())) if losses_c > 0 else 0.0
                gross_profit = float(df[wins_mask]["total_profit"].sum())
                gross_loss = float(abs(df[losses_mask]["total_profit"].sum()))
                profit_factor = (gross_profit / gross_loss) if gross_loss != 0 else float("inf")
                expectancy = (win_rate/100.0 * avg_win) - ((100.0 - win_rate)/100.0 * avg_loss)
                total_pnl = float(total_profit.sum())
                avg_pnl = float(total_profit.mean())
                return {
                    "count": n,
                    "wins": wins_c,
                    "losses": losses_c,
                    "win_rate": float(win_rate),
                    "best_trade": best_trade,
                    "worst_trade": worst_trade,
                    "avg_win": avg_win,
                    "avg_loss": avg_loss,
                    "profit_factor": float(profit_factor),
                    "expectancy": float(expectancy),
                    "total_pnl": total_pnl,
                    "avg_pnl": avg_pnl,
                }

            by_weekday: Dict[int, Dict[str, Any]] = {}
            for wd, g in ops_df.groupby("weekday"):
                by_weekday[int(wd)] = _agg_trade_stats(g)
            stats["period_stats_by_weekday"] = by_weekday

            by_hour: Dict[int, Dict[str, Any]] = {}
            for hr, g in ops_df.groupby("hour"):
                by_hour[int(hr)] = _agg_trade_stats(g)
            stats["period_stats_by_hour"] = by_hour

            # Nested: for each weekday, stats by hour within that weekday
            by_wd_hr: Dict[int, Dict[int, Dict[str, Any]]] = {}
            for wd, g_wd in ops_df.groupby("weekday"):
                inner: Dict[int, Dict[str, Any]] = {}
                for hr, g_hr in g_wd.groupby("hour"):
                    inner[int(hr)] = _agg_trade_stats(g_hr)
                by_wd_hr[int(wd)] = inner
            stats["period_stats_by_weekday_hour"] = by_wd_hr

            # Average operations per N candles (if bar count can be inferred from backtest)
            def _infer_bar_count(bt: Any, start: pd.Timestamp, end: pd.Timestamp) -> Optional[int]:
                candidates = [
                    getattr(bt, "bars_df", None),
                    getattr(bt, "price_df", None),
                    getattr(bt, "candles_df", None),
                    getattr(bt, "history", None),
                    getattr(bt, "data", None),
                    getattr(getattr(bt, "market", None), "bars_df", None),
                ]
                for df in candidates:
                    if df is None:
                        continue
                    try:
                        if hasattr(df, "index") and isinstance(df.index, pd.DatetimeIndex):
                            return int(df.loc[(df.index >= start) & (df.index <= end)].shape[0])
                        if isinstance(df, pd.DataFrame) and "time" in df.columns:
                            dd = df.copy()
                            dd["time"] = pd.to_datetime(dd["time"])  # ensure
                            return int(dd[(dd["time"] >= start) & (dd["time"] <= end)].shape[0])
                    except Exception:
                        continue
                return None

            bar_count = _infer_bar_count(backtest, ops_df["time"].min(), ops_df["time"].max())
            if bar_count and bar_count > 0:
                ratios = {}
                for n in [10, 50, 100, 500]:
                    ratios[str(n)] = float(total_ops / bar_count * n)
                stats["ops_per_n_candles"] = ratios
                stats["bars_covered"] = int(bar_count)
            else:
                stats["ops_per_n_candles"] = None
                stats["bars_covered"] = None

            # Dataset coverage: total candles available in backtest and interval (first/last)
            def _pick_time_series(bt: Any) -> Optional[pd.Series]:
                candidates = [
                    getattr(bt, "bars_df", None),
                    getattr(bt, "price_df", None),
                    getattr(bt, "candles_df", None),
                    getattr(bt, "history", None),
                    getattr(bt, "data", None),
                    getattr(getattr(bt, "market", None), "bars_df", None),
                ]
                for df in candidates:
                    if df is None:
                        continue
                    try:
                        if hasattr(df, "index") and isinstance(df.index, pd.DatetimeIndex) and len(df.index) > 0:
                            return df.index.to_series()
                        if isinstance(df, pd.DataFrame) and "time" in df.columns and len(df) > 0:
                            dd = df.copy()
                            dd["time"] = pd.to_datetime(dd["time"])  # ensure
                            return dd["time"]
                    except Exception:
                        continue
                return None

            ts_series = _pick_time_series(backtest)
            if ts_series is not None and len(ts_series) > 0:
                try:
                    stats["candles_total_count"] = int(len(ts_series))
                    stats["candles_range_start"] = pd.to_datetime(ts_series.min())
                    stats["candles_range_end"] = pd.to_datetime(ts_series.max())
                except Exception:
                    stats["candles_total_count"] = None
                    stats["candles_range_start"] = None
                    stats["candles_range_end"] = None
            else:
                stats["candles_total_count"] = None
                stats["candles_range_start"] = None
                stats["candles_range_end"] = None
        else:
            stats["avg_trade_duration_days"] = None
            stats["trade_duration_candles_summary"] = None
            stats["inter_trade_gap_candles_summary"] = None
            stats["ops_by_weekday"] = None
            stats["ops_by_hour"] = None
            stats["ops_per_n_candles"] = None
            stats["bars_covered"] = None
            stats["candles_total_count"] = None
            stats["candles_range_start"] = None
            stats["candles_range_end"] = None
            stats["period_stats_by_weekday"] = None
            stats["period_stats_by_hour"] = None
            stats["period_stats_by_weekday_hour"] = None
    else:
        # No trades
        stats.update({
            "total_pnl": 0.0,
            "avg_pnl": 0.0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "total_swap": 0.0,
            "total_commission": 0.0,
            "equity_curve": pd.Series([initial_balance]),
            "max_drawdown": 0.0,
            "max_dd_pct": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "win_loss_ratio": float("inf"),
            "profit_factor": float("inf"),
            "risk_reward_ratio": float("inf"),
            "expectancy": 0.0,
            "returns_std": 0.0,
            "sharpe_ratio": 0.0,
            "initial_balance": float(initial_balance),
            "final_balance": float(getattr(backtest, "balance", initial_balance)),
            "actual_total_pnl": float(getattr(backtest, "balance", initial_balance)) - float(initial_balance),
            "recovery_factor": float("inf"),
            "avg_trade_duration_days": None,
        })

    return stats


# ===== Markdown Report =====
def render_markdown_report(*, stats: Dict[str, Any], params: Optional[Dict[str, Any]] = None, notes: Optional[List[str]] = None, extra_sections: Optional[Dict[str, str]] = None) -> str:
    """Renders a markdown string with all stats. Strategies can pass extra_sections to append custom content."""
    params = params or {}
    notes = notes or ["All values include swap and commission costs", "Statistics are based on closed trades only"]

    symbol = params.get("symbol", "UNKNOWN")
    timeframe = params.get("timeframe_name", "N/A")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = []
    md.append("# Backtest Results")
    md.append("")

    # Additional operation insights
    dur = stats.get("trade_duration_candles_summary")
    gaps = stats.get("inter_trade_gap_candles_summary")
    if dur or gaps:
        md.append("## Operation Timing")
        if dur:
            md.append(f"- **Trade Duration (median):** {dur['median']:.0f} candles  ")
            md.append(f"- **Trade Duration (mean):** {dur['mean']:.0f} candles  ")
            md.append(f"- **Trade Duration (min/max):** {dur['min']:.0f} / {dur['max']:.0f} candles  ")
        if gaps:
            md.append(f"- **Inter-Trade Gap (median):** {gaps['median']:.0f} candles  ")
            md.append(f"- **Inter-Trade Gap (mean):** {gaps['mean']:.0f} candles  ")
        md.append("")

    if stats.get("ops_by_weekday"):
        by_wd = ", ".join(f"{k}:{v}" for k, v in stats["ops_by_weekday"].items())
        md.append("## Signals Distribution")
        md.append(f"- **By Weekday (0=Mon):** {by_wd}")
        if stats.get("ops_by_hour"):
            by_hr = ", ".join(f"{k}:{v}" for k, v in stats["ops_by_hour"].items())
            md.append(f"- **By Hour (0-23):** {by_hr}")
        if stats.get("ops_per_n_candles"):
            ops_rate = ", ".join(f"{k}:{v:.2f}" for k, v in stats["ops_per_n_candles"].items())
            md.append(f"- **Ops per N Candles:** {ops_rate}")
        md.append("")

    # Dataset Coverage
    if stats.get("candles_total_count") is not None:
        md.append("## Data Coverage")
        md.append(f"- **Candles (total):** {stats['candles_total_count']}")
        if stats.get("candles_range_start") is not None and stats.get("candles_range_end") is not None:
            try:
                start_str = pd.to_datetime(stats["candles_range_start"]).strftime("%Y-%m-%d %H:%M:%S")
                end_str = pd.to_datetime(stats["candles_range_end"]).strftime("%Y-%m-%d %H:%M:%S")
                md.append(f"- **Interval:** {start_str} → {end_str}")
            except Exception:
                pass
        md.append("")

    # Period performance tables
    def _append_period_table(title: str, items: Dict[int, Dict[str, Any]], label_map: Dict[int, str]):
        if not items:
            return
        md.append(f"## {title}")
        md.append("| Period | Trades | Wins | Losses | Win Rate % | Best | Worst | Avg Win | Avg Loss | Profit Factor | Expectancy | Total PnL | Avg PnL |")
        md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for k in sorted(items.keys()):
            s = items[k] or {}
            name = label_map.get(k, str(k))
            md.append(
                "| "
                f"{name} | "
                f"{s.get('count', 0)} | "
                f"{s.get('wins', 0)} | "
                f"{s.get('losses', 0)} | "
                f"{s.get('win_rate', 0.0):.1f} | "
                f"{s.get('best_trade', 0.0):.2f} | "
                f"{s.get('worst_trade', 0.0):.2f} | "
                f"{s.get('avg_win', 0.0):.2f} | "
                f"{s.get('avg_loss', 0.0):.2f} | "
                f"{s.get('profit_factor', float('inf')):.2f} | "
                f"{s.get('expectancy', 0.0):.2f} | "
                f"{s.get('total_pnl', 0.0):.2f} | "
                f"{s.get('avg_pnl', 0.0):.2f} |"
            )
        md.append("")

    weekday_labels = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    if stats.get("period_stats_by_weekday"):
        _append_period_table("Period Performance by Weekday", stats["period_stats_by_weekday"], weekday_labels)
    if stats.get("period_stats_by_hour"):
        hour_labels = {i: f"{i:02d}h" for i in range(24)}
        _append_period_table("Period Performance by Hour", stats["period_stats_by_hour"], hour_labels)
    if stats.get("period_stats_by_weekday_hour"):
        md.append("## Period Performance by Weekday and Hour")
        by_wd_hr = stats["period_stats_by_weekday_hour"] or {}
        for wd in sorted(by_wd_hr.keys()):
            inner = by_wd_hr.get(wd) or {}
            md.append(f"### {weekday_labels.get(wd, str(wd))}")
            md.append("| Hour | Trades | Wins | Losses | Win Rate % | Best | Worst | Avg Win | Avg Loss | Profit Factor | Expectancy | Total PnL | Avg PnL |")
            md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
            for hr in sorted(inner.keys()):
                s = inner[hr] or {}
                label = f"{int(hr):02d}h"
                md.append(
                    "| "
                    f"{label} | "
                    f"{s.get('count', 0)} | "
                    f"{s.get('wins', 0)} | "
                    f"{s.get('losses', 0)} | "
                    f"{s.get('win_rate', 0.0):.1f} | "
                    f"{s.get('best_trade', 0.0):.2f} | "
                    f"{s.get('worst_trade', 0.0):.2f} | "
                    f"{s.get('avg_win', 0.0):.2f} | "
                    f"{s.get('avg_loss', 0.0):.2f} | "
                    f"{s.get('profit_factor', float('inf')):.2f} | "
                    f"{s.get('expectancy', 0.0):.2f} | "
                    f"{s.get('total_pnl', 0.0):.2f} | "
                    f"{s.get('avg_pnl', 0.0):.2f} |"
                )
            md.append("")
    md.append(f"**Symbol:** {symbol}  ")
    md.append(f"**Timeframe:** {timeframe}  ")
    md.append(f"**Date:** {timestamp}")
    md.append("")

    md.append("## Performance Summary")
    md.append(f"- **Initial Balance:** ${stats['initial_balance']:,.2f}")
    md.append(f"- **Final Balance:** ${stats['final_balance']:,.2f}")
    md.append(f"- **Total PnL:** ${stats['actual_total_pnl']:,.2f} ({(stats['actual_total_pnl']/stats['initial_balance']*100):.2f}%)")
    md.append(f"- **Total Trades:** {stats['total_ops']:,}")
    md.append(f"- **Win Rate:** {stats['win_rate']:.1f}%")
    md.append(f"- **Profit Factor:** {stats['profit_factor']:.2f}")
    md.append(f"- **Sharpe Ratio:** {stats['sharpe_ratio']:.2f}")
    md.append(f"- **Max Drawdown:** ${abs(stats['max_drawdown']):,.2f} ({stats['max_dd_pct']:.2f}%)")
    md.append(f"- **Recovery Factor:** {stats['recovery_factor']:.2f}")
    md.append("")

    md.append("## Trade Statistics")
    md.append(f"- **Winning Trades:** {stats['wins']:,}")
    md.append(f"- **Losing Trades:** {stats['losses']:,}")
    md.append(f"- **Best Trade:** ${stats['best_trade']:,.2f}")
    md.append(f"- **Worst Trade:** ${stats['worst_trade']:,.2f}")
    md.append(f"- **Average Win:** ${stats['avg_win']:,.2f}")
    md.append(f"- **Average Loss:** ${stats['avg_loss']:,.2f}")
    md.append(f"- **Win/Loss Ratio:** {stats['win_loss_ratio']:.2f}:1")
    md.append(f"- **Risk/Reward Ratio:** {stats['risk_reward_ratio']:.2f}:1")
    md.append(f"- **Expectancy:** ${stats['expectancy']:,.2f}")
    md.append("")

    md.append("## Costs")
    md.append(f"- **Total Swap:** ${stats['total_swap']:,.2f}")
    md.append(f"- **Total Commission:** ${stats['total_commission']:,.2f}")
    md.append(f"- **Total Costs:** ${stats['total_swap'] + stats['total_commission']:,.2f}")
    md.append("")

    eq = stats.get("equity_curve")
    if eq is not None and len(eq) > 0:
        md.append("## Equity Curve")
        md.append(f"- **Peak Equity:** ${eq.max():,.2f}")
        md.append(f"- **Trough Equity:** ${eq.min():,.2f}")
        md.append(f"- **Final Return:** {(((eq.iloc[-1] / eq.iloc[0]) - 1) * 100):.2f}%")
        md.append("")

    md.append("## Strategy Parameters")
    for k, v in params.items():
        if k.endswith("_name"):
            continue
        md.append(f"- **{k}:** {v}")
    md.append("")

    if extra_sections:
        for title, content in extra_sections.items():
            md.append(f"## {title}")
            md.append(content.rstrip())
            md.append("")

    md.append("## Notes")
    for n in notes:
        md.append(f"- {n}")

    return "\n".join(md) + "\n"


def save_report_markdown(content: str, *, script_file: str, symbol: str) -> str:
    """Saves the markdown content alongside the given script file. Returns the file path."""
    script_dir = os.path.dirname(os.path.abspath(script_file))
    fname = f"backtest_results_{symbol}.md"
    fpath = os.path.join(script_dir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    return fpath
