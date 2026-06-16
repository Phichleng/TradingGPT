# TradingGPT API (v1)

Base path: `/v1`

| Method | Path | Body | Returns |
|---|---|---|---|
| GET  | `/health` | – | `{status: ok}` |
| GET  | `/ready` | – | readiness probe |
| POST | `/webhook/tradingview` | `TradingViewAlert` | `{status, idempotency_key}` |
| POST | `/analyze` | `{market, timeframe}` | `AnalysisReport` |
| GET  | `/analysis/{id}` | – | stored `AnalysisReport` |
| GET  | `/analysis?market=&limit=` | – | history |
| POST | `/journals` | `JournalIn` | created journal (triggers RAG re-ingest) |
| GET  | `/journals?market=` | – | list |
| POST | `/knowledge/ingest` | doc upload | `{chunks}` |
| GET/PUT | `/settings` | `UserSetting` | risk + preferences |
| WS   | `/stream` | – | pushes `analysis_ready` events |

## TradingViewAlert payload
```json
{ "secret": "...", "market": "XAUUSD", "timeframe": "15m",
  "price": 2359.2, "event": "alert_fired", "strategy_hint": "ict",
  "nonce": "{{timenow}}", "bar_time": "{{time}}" }
```
Auth: shared `secret` in body (TradingView can't set headers) + idempotency on
`sha256(market|timeframe|nonce)`. Allowlist TradingView IPs at the proxy; TLS only.

## AnalysisReport (response)
See `backend/app/schemas/analysis.py` — includes market, timeframe, regime,
selected_strategy, trend, structure, ict/smc/crt scores, strategy_scores,
entry_zone, stop_loss, take_profit, risk_reward, confidence, risk_status,
warnings, verdict, reasoning.
