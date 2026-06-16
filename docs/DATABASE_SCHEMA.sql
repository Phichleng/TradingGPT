-- TradingGPT — PostgreSQL + TimescaleDB schema (production).
-- Dev uses SQLite via the same SQLAlchemy models (no hypertable/JSONB types).

CREATE TABLE markets (
    id          SERIAL PRIMARY KEY,
    symbol      TEXT UNIQUE NOT NULL,
    asset_class TEXT NOT NULL,
    phase       SMALLINT NOT NULL DEFAULT 1,
    pip_size    NUMERIC NOT NULL,
    tick_value  NUMERIC,
    enabled     BOOLEAN DEFAULT TRUE,
    sessions_tz TEXT DEFAULT 'America/New_York',
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE candles (
    market_id INT NOT NULL REFERENCES markets(id),
    timeframe TEXT NOT NULL,
    ts        TIMESTAMPTZ NOT NULL,
    open NUMERIC, high NUMERIC, low NUMERIC, close NUMERIC, volume NUMERIC,
    PRIMARY KEY (market_id, timeframe, ts)
);
SELECT create_hypertable('candles','ts', chunk_time_interval => INTERVAL '7 days');
CREATE INDEX ON candles (market_id, timeframe, ts DESC);

CREATE TABLE knowledge_documents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_type     TEXT NOT NULL,
    title        TEXT NOT NULL,
    source_path  TEXT,
    market_id    INT REFERENCES markets(id),
    metadata     JSONB DEFAULT '{}',
    content_hash TEXT UNIQUE,
    chunk_count  INT DEFAULT 0,
    ingested_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE journals (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id   INT REFERENCES markets(id),
    direction   TEXT, strategy TEXT,
    entry_ts    TIMESTAMPTZ, exit_ts TIMESTAMPTZ,
    entry_price NUMERIC, exit_price NUMERIC,
    stop_loss   NUMERIC, take_profit NUMERIC,
    rr_planned  NUMERIC, rr_realized NUMERIC,
    outcome     TEXT, pnl_pct NUMERIC,
    setup_notes TEXT, mistakes TEXT, screenshot_url TEXT,
    tags        TEXT[], created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE backtests (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy     TEXT NOT NULL, market_id INT REFERENCES markets(id),
    timeframe    TEXT, period_start DATE, period_end DATE,
    n_trades     INT, win_rate NUMERIC, avg_rr NUMERIC,
    profit_factor NUMERIC, max_drawdown NUMERIC,
    params JSONB, equity_curve JSONB, created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE analysis_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id       INT REFERENCES markets(id),
    timeframe       TEXT NOT NULL,
    requested_at    TIMESTAMPTZ DEFAULT now(),
    trigger_source  TEXT,
    regime          TEXT, selected_strategy TEXT, confidence NUMERIC,
    ict_score NUMERIC, smc_score NUMERIC, crt_score NUMERIC,
    structure JSONB, strategy_scores JSONB,
    risk_passed BOOLEAN, risk_reasons TEXT[],
    entry_zone NUMRANGE, stop_loss NUMERIC, take_profit NUMERIC, rr NUMERIC,
    report_md TEXT, report_json JSONB,
    llm_model TEXT, rag_doc_ids UUID[], latency_ms INT
);
CREATE INDEX ON analysis_logs (market_id, requested_at DESC);

CREATE TABLE user_settings (
    id SERIAL PRIMARY KEY, user_id TEXT,
    risk_per_trade NUMERIC DEFAULT 0.01, min_rr NUMERIC DEFAULT 2.0,
    daily_loss_limit NUMERIC DEFAULT 0.03, weekly_loss_limit NUMERIC DEFAULT 0.06,
    account_balance NUMERIC, enabled_strategies TEXT[],
    preferences JSONB DEFAULT '{}', updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key TEXT UNIQUE,
    received_at TIMESTAMPTZ DEFAULT now(),
    payload JSONB, status TEXT DEFAULT 'received'
);
