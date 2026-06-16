from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(tags=["paper-trading"])


@router.get("/paper-trades")
def list_trades(limit: int = Query(100, ge=1, le=500)):
    from app.paper_trading.positions import get_all_positions
    return get_all_positions(limit=limit)


@router.get("/paper-trades/open")
def open_trades():
    from app.paper_trading.positions import get_open_positions
    return get_open_positions()


@router.get("/paper-trades/summary")
def trade_summary():
    from app.paper_trading.positions import get_summary
    return get_summary()


@router.delete("/paper-trades/{trade_id}")
def close_trade(trade_id: str, exit_price: float):
    from app.paper_trading.positions import close_position
    result = close_position(trade_id, exit_price, reason="manual")
    if result is None:
        raise HTTPException(404, "Trade not found or already closed")
    return result
