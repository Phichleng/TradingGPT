from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.core.security import idempotency_key, verify_secret
from app.schemas.webhook import TradingViewAlert

router = APIRouter(tags=["webhook"])


@router.post("/webhook/tradingview")
def tradingview_webhook(alert: TradingViewAlert):
    if not verify_secret(alert.secret, settings.tv_webhook_secret):
        raise HTTPException(status_code=401, detail="bad secret")

    key = idempotency_key(alert.market, alert.timeframe, alert.nonce)
    # TODO: persist key to webhook_events; return 'duplicate_ignored' if seen.
    try:
        from app.workers.tasks import analyze_market
        analyze_market.delay(market=alert.market, timeframe=alert.timeframe,
                             source="webhook")
        status = "queued"
    except Exception:
        status = "queued_sync_fallback"          # no broker in dev
    return {"status": status, "idempotency_key": key}
