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

    total_ops = len(ops_df)
    stats["total_ops"] = total_ops

    if total_ops > 0:
        stats["total_pnl"] = float(ops_df["total_profit"].sum())
        stats["avg_pnl"] = float(ops_df["total_profit"].mean())
        stats["wins"] = int((ops_df["total_profit"] > 0).sum())
        stats["losses"] = int((ops_df["total_profit"] < 0).sum())
        stats["win_rate"] = (stats["wins"] / total_ops) * 100.0 if total_ops else 0.0

        trade_profits = ops_df["total_profit"].copy()
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
        stats["total_swap"] = float(ops_df["swap"].sum())
        stats["total_commission"] = float(ops_df["commission"].sum())

        # Equity curve based on net profit per trade (without initial deposit)
        equity_curve = initial_balance + ops_df["profit"].cumsum()
        stats["equity_curve"] = equity_curve
        rolling_max = equity_curve.cummax()
        drawdown = equity_curve - rolling_max
        stats["max_drawdown"] = float(drawdown.min()) if len(drawdown) else 0.0
        stats["max_dd_pct"] = (stats["max_drawdown"] / float(rolling_max.max()) * 100.0) if float(rolling_max.max() or 0) else 0.0

        # Derived risk metrics
        wins = stats["wins"]
        losses = stats["losses"]
        avg_win = float(ops_df[ops_df["total_profit"] > 0]["total_profit"].mean()) if wins > 0 else 0.0
        avg_loss = float(abs(ops_df[ops_df["total_profit"] < 0]["total_profit"].mean())) if losses > 0 else 0.0
        stats["avg_win"], stats["avg_loss"] = avg_win, avg_loss
        stats["win_loss_ratio"] = (avg_win / avg_loss) if avg_loss != 0 else float("inf")

        gross_profit = float(ops_df[ops_df["total_profit"] > 0]["total_profit"].sum())
        gross_loss = float(abs(ops_df[ops_df["total_profit"] < 0]["total_profit"].sum()))
        stats["profit_factor"] = (gross_profit / gross_loss) if gross_loss != 0 else float("inf")

        stats["risk_reward_ratio"] = (avg_win / avg_loss) if avg_loss != 0 else float("inf")
        stats["expectancy"] = (stats["win_rate"]/100.0 * avg_win) - ((100.0 - stats["win_rate"]) / 100.0 * avg_loss)

        returns_std = float(ops_df["total_profit"].std() or 0)
        stats["returns_std"] = returns_std
        stats["sharpe_ratio"] = (stats["avg_pnl"] / returns_std) if returns_std != 0 else 0.0

        final_balance = float(getattr(backtest, "balance", initial_balance))
        stats["initial_balance"] = float(initial_balance)
        stats["final_balance"] = final_balance
        stats["actual_total_pnl"] = final_balance - float(initial_balance)
        stats["recovery_factor"] = (stats["actual_total_pnl"] / abs(stats["max_drawdown"])) if stats["max_drawdown"] != 0 else float("inf")

        # Optional time-based stats
        if "time" in ops_df.columns and len(ops_df) > 1:
            ops_df = ops_df.copy()
            ops_df["time"] = pd.to_datetime(ops_df["time"])  # ensure dtype
            trade_duration_days = (ops_df["time"].max() - ops_df["time"].min()).days
            stats["avg_trade_duration_days"] = trade_duration_days / len(ops_df) if len(ops_df) else 0
        else:
            stats["avg_trade_duration_days"] = None
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
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"backtest_results_{symbol}_{ts}.md"
    fpath = os.path.join(script_dir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    return fpath
