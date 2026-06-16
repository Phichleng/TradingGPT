from fastapi import APIRouter

from app.api.v1 import analysis, backtest, chat, health, journals, paper_trading, webhook

api_router = APIRouter(prefix="/v1")
api_router.include_router(health.router)
api_router.include_router(webhook.router)
api_router.include_router(analysis.router)
api_router.include_router(journals.router)
api_router.include_router(paper_trading.router)
api_router.include_router(backtest.router)
api_router.include_router(chat.router)
