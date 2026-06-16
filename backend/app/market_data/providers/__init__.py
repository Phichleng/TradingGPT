from __future__ import annotations

from app.market_data.provider import BaseProvider


def get_provider() -> BaseProvider:
    from app.config import settings
    if getattr(settings, "market_data_provider", "mock") == "yfinance":
        from app.market_data.providers.yfinance_provider import YFinanceProvider
        return YFinanceProvider()
    from app.market_data.providers.mock_provider import MockProvider
    return MockProvider()
