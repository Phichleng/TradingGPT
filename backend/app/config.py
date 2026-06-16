from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_name: str = "TradingGPT"
    env: str = "dev"

    database_url: str = "sqlite:///./tradinggpt.db"
    redis_url: str = "redis://localhost:6379/0"
    vector_db_path: str = "./vector_db"

    ollama_url: str = "http://localhost:11434/v1"
    llm_model: str = "tradinggpt-analyst"

    tv_webhook_secret: str = "change-me"
    tv_hmac_key: str = "change-me-too"

    market_data_provider: str = "mock"  # "mock" | "yfinance"

    # Comma-separated lists parsed at startup
    scheduler_markets: str = "XAUUSD"
    scheduler_timeframes: str = "15,60"

    risk_per_trade: float = 0.01
    min_rr: float = 2.0
    daily_loss_limit: float = 0.03
    weekly_loss_limit: float = 0.06
    account_balance: float = 10000.0

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    paper_trading_enabled: bool = True


settings = Settings()
