"""Aggregate performance metrics from a list of simulated trades."""
from __future__ import annotations


def compute_metrics(trades: list[dict]) -> dict:
    """
    trades: list of dicts with keys: ts, direction, strategy, rr, outcome ('win'|'loss')
    Returns a performance summary dict.
    """
    if not trades:
        return {
            "total_trades": 0, "wins": 0, "losses": 0,
            "win_rate": 0.0, "avg_rr": 0.0, "profit_factor": 0.0,
            "net_rr": 0.0, "max_drawdown_rr": 0.0, "trades": [],
        }

    wins = [t for t in trades if t["outcome"] == "win"]
    losses = [t for t in trades if t["outcome"] == "loss"]

    gross_win = sum(t["rr"] for t in wins)
    gross_loss = sum(t["rr"] for t in losses)

    win_rate = len(wins) / len(trades) * 100
    avg_rr = (gross_win - gross_loss) / len(trades)
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (gross_win or 0)
    net_rr = gross_win - gross_loss

    # Simple drawdown: running net RR dip from peak
    running = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        running += t["rr"] if t["outcome"] == "win" else -t["rr"]
        peak = max(peak, running)
        dd = peak - running
        max_dd = max(max_dd, dd)

    return {
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "avg_rr": round(avg_rr, 2),
        "profit_factor": round(profit_factor, 2),
        "net_rr": round(net_rr, 2),
        "max_drawdown_rr": round(max_dd, 2),
        "trades": trades[-30:],
    }
