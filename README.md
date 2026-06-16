# TradingGPT

Institutional-grade AI Trading Analyst: deterministic ICT/SMC/CRT engines +
strategy selection + non-bypassable risk gate + RAG over your journals/playbooks
+ a local LLM that *explains* (never invents) setups.

> Decision-support, not a profit guarantee. The risk engine is a hard gate.

## Quickstart (Phase 1, no infra)
```bash
pip install -e ".[dev]"          # or: pip install pandas numpy fastapi pytest ...
make test                        # 9 deterministic engine/risk/selector tests pass
cd backend && uvicorn app.main:app --reload
curl -X POST localhost:8000/v1/analyze -H 'content-type: application/json' \
     -d '{"market":"XAUUSD","timeframe":"15m"}'
```

## Full stack
```bash
make models                      # pull Qwen3 + embeddings into Ollama (host)
make up                          # FastAPI + worker + Timescale + Qdrant + Redis
```

## Layout
- `backend/app/engines` — deterministic detection (pure, fully tested)
- `backend/app/strategies` — 9 strategies behind a registry
- `backend/app/selection` / `risk` — pick best + hard risk gate
- `backend/app/rag` / `llm` — retrieval + local-LLM synthesis
- `backend/app/orchestrator/pipeline.py` — wires it all in order
- `docs/` — DB schema, API reference, class/sequence diagrams

## What's implemented vs stubbed (Phase 1 skeleton)
- **Implemented & tested:** primitives, market structure, ICT/SMC/CRT detectors +
  scores, regime, selector, risk gate, ICT strategy proposal, pipeline, mock data,
  FastAPI routes.
- **Stubbed (clear TODOs):** 8 strategy `propose()` bodies, RAG ingest against a
  live store, LLM call (needs Ollama), DB persistence in repositories, frontend.
