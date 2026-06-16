"""SQLAlchemy ORM — mirrors the DDL in docs/DATABASE_SCHEMA.sql. On Postgres,
'candles' becomes a TimescaleDB hypertable (see migration)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Integer,
                        Numeric, String, Text, JSON)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Market(Base):
    __tablename__ = "markets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, unique=True)
    asset_class: Mapped[str] = mapped_column(String)
    phase: Mapped[int] = mapped_column(Integer, default=1)
    pip_size: Mapped[float] = mapped_column(Numeric)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Candle(Base):
    __tablename__ = "candles"
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"), primary_key=True)
    timeframe: Mapped[str] = mapped_column(String, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[float] = mapped_column(Numeric)
    high: Mapped[float] = mapped_column(Numeric)
    low: Mapped[float] = mapped_column(Numeric)
    close: Mapped[float] = mapped_column(Numeric)
    volume: Mapped[float | None] = mapped_column(Numeric, nullable=True)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    doc_type: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    source_path: Mapped[str | None] = mapped_column(String, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    doc_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Journal(Base):
    __tablename__ = "journals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    market_id: Mapped[int | None] = mapped_column(ForeignKey("markets.id"), nullable=True)
    direction: Mapped[str | None] = mapped_column(String, nullable=True)
    strategy: Mapped[str | None] = mapped_column(String, nullable=True)
    entry_price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    rr_realized: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String, nullable=True)
    pnl_pct: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    setup_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    mistakes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Backtest(Base):
    __tablename__ = "backtests"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    strategy: Mapped[str] = mapped_column(String)
    market_id: Mapped[int | None] = mapped_column(ForeignKey("markets.id"), nullable=True)
    win_rate: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    avg_rr: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    profit_factor: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)


class AnalysisLog(Base):
    __tablename__ = "analysis_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    market_id: Mapped[int | None] = mapped_column(ForeignKey("markets.id"), nullable=True)
    timeframe: Mapped[str] = mapped_column(String)
    selected_strategy: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ict_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    smc_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    crt_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    report_json: Mapped[dict] = mapped_column(JSON, default=dict)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserSetting(Base):
    __tablename__ = "user_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_per_trade: Mapped[float] = mapped_column(Float, default=0.01)
    min_rr: Mapped[float] = mapped_column(Float, default=2.0)
    daily_loss_limit: Mapped[float] = mapped_column(Float, default=0.03)
    weekly_loss_limit: Mapped[float] = mapped_column(Float, default=0.06)
    account_balance: Mapped[float | None] = mapped_column(Float, nullable=True)


class PaperTrade(Base):
    __tablename__ = "paper_trades"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    market: Mapped[str] = mapped_column(String)
    timeframe: Mapped[str] = mapped_column(String)
    direction: Mapped[str] = mapped_column(String)           # 'long' | 'short'
    strategy: Mapped[str | None] = mapped_column(String, nullable=True)
    entry_price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    entry_zone_lo: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    entry_zone_hi: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    stop_loss: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    planned_rr: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    realized_rr: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="open")   # 'open' | 'closed'
    outcome: Mapped[str | None] = mapped_column(String, nullable=True)  # 'win' | 'loss'
    pnl_pct: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    close_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    analysis_report: Mapped[dict] = mapped_column(JSON, default=dict)
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    idempotency_key: Mapped[str] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String, default="received")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
