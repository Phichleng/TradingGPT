"""Paper trading position management — open, close, and query simulated trades."""
from __future__ import annotations

import logging
from datetime import datetime

from app.db.models.tables import PaperTrade
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def open_position(report: dict) -> str | None:
    """Open a paper trade from a valid analysis report. Returns trade ID or None."""
    verdict = report.get("verdict", "")
    if not verdict.startswith("valid_"):
        return None

    entry_zone = report.get("entry_zone") or [0.0, 0.0]
    entry_price = (float(entry_zone[0]) + float(entry_zone[1])) / 2
    direction = "long" if "long" in verdict else "short"

    with SessionLocal() as session:
        trade = PaperTrade(
            market=report["market"],
            timeframe=report["timeframe"],
            direction=direction,
            strategy=report.get("selected_strategy"),
            entry_price=entry_price,
            entry_zone_lo=float(entry_zone[0]),
            entry_zone_hi=float(entry_zone[1]),
            stop_loss=report.get("stop_loss"),
            take_profit=report.get("take_profit"),
            planned_rr=report.get("risk_reward"),
            confidence=report.get("confidence"),
            status="open",
            analysis_report=report,
        )
        session.add(trade)
        session.commit()
        session.refresh(trade)
        logger.info("paper | opened %s %s/%s rr=%.1f",
                    direction.upper(), report["market"], report["timeframe"],
                    float(report.get("risk_reward") or 0))
        return trade.id


def close_position(trade_id: str, exit_price: float, reason: str) -> dict | None:
    """Close an open paper trade. Returns the trade dict or None if not found/already closed."""
    with SessionLocal() as session:
        trade = session.get(PaperTrade, trade_id)
        if not trade or trade.status != "open":
            return None

        entry = float(trade.entry_price or 0)
        if entry == 0:
            return None

        if trade.direction == "long":
            pnl_pct = (exit_price - entry) / entry * 100
        else:
            pnl_pct = (entry - exit_price) / entry * 100

        sl = float(trade.stop_loss or 0)
        tp = float(trade.take_profit or 0)
        risk_dist = abs(entry - sl) if sl else 0
        reward_dist = abs(exit_price - entry)
        realized_rr = (reward_dist / risk_dist) if risk_dist else 0

        trade.exit_price = exit_price
        trade.status = "closed"
        trade.outcome = "win" if pnl_pct > 0 else "loss"
        trade.pnl_pct = round(pnl_pct, 4)
        trade.realized_rr = round(realized_rr, 2)
        trade.close_reason = reason
        trade.closed_at = datetime.utcnow()
        session.commit()

        result = _to_dict(trade)
        logger.info("paper | closed %s %s → %s pnl=%.2f%%",
                    trade.market, trade.direction, trade.outcome, pnl_pct)
        return result


def get_open_positions() -> list[dict]:
    with SessionLocal() as session:
        rows = (session.query(PaperTrade)
                .filter(PaperTrade.status == "open")
                .order_by(PaperTrade.opened_at.desc())
                .all())
        return [_to_dict(r) for r in rows]


def get_all_positions(limit: int = 100) -> list[dict]:
    with SessionLocal() as session:
        rows = (session.query(PaperTrade)
                .order_by(PaperTrade.opened_at.desc())
                .limit(limit)
                .all())
        return [_to_dict(r) for r in rows]


def get_summary() -> dict:
    """Aggregate stats: win rate, total P&L, open count."""
    with SessionLocal() as session:
        all_trades = session.query(PaperTrade).all()
        closed = [t for t in all_trades if t.status == "closed"]
        wins = [t for t in closed if t.outcome == "win"]
        total_pnl = sum(float(t.pnl_pct or 0) for t in closed)
        return {
            "open": len([t for t in all_trades if t.status == "open"]),
            "closed": len(closed),
            "wins": len(wins),
            "losses": len(closed) - len(wins),
            "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0.0,
            "total_pnl_pct": round(total_pnl, 2),
        }


def _to_dict(t: PaperTrade) -> dict:
    return {
        "id": t.id,
        "market": t.market,
        "timeframe": t.timeframe,
        "direction": t.direction,
        "strategy": t.strategy,
        "entry_price": float(t.entry_price) if t.entry_price is not None else None,
        "entry_zone_lo": float(t.entry_zone_lo) if t.entry_zone_lo is not None else None,
        "entry_zone_hi": float(t.entry_zone_hi) if t.entry_zone_hi is not None else None,
        "stop_loss": float(t.stop_loss) if t.stop_loss is not None else None,
        "take_profit": float(t.take_profit) if t.take_profit is not None else None,
        "exit_price": float(t.exit_price) if t.exit_price is not None else None,
        "planned_rr": float(t.planned_rr) if t.planned_rr is not None else None,
        "realized_rr": float(t.realized_rr) if t.realized_rr is not None else None,
        "confidence": t.confidence,
        "status": t.status,
        "outcome": t.outcome,
        "pnl_pct": float(t.pnl_pct) if t.pnl_pct is not None else None,
        "close_reason": t.close_reason,
        "opened_at": t.opened_at.isoformat() if t.opened_at else None,
        "closed_at": t.closed_at.isoformat() if t.closed_at else None,
    }
