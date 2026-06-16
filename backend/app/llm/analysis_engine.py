from __future__ import annotations

import json
from pathlib import Path

from app.llm.client import chat

_PROMPTS = Path(__file__).parent / "prompts"


class LLMAnalysisEngine:
    """Synthesises a human-readable reasoning string from deterministic outputs +
    retrieved knowledge. NEVER invents price levels."""

    def __init__(self):
        self.system = (_PROMPTS / "analyst_system.md").read_text()

    def explain(self, report: dict, *, retriever=None) -> str:
        rag = {}
        if retriever and report.get("selected_strategy"):
            rag = retriever.retrieve(
                market=report["market"], strategy=report["selected_strategy"],
                regime={"regime": report["market_regime"]},
                structure_summary={"trend": report["trend"],
                                   "structure_status": report["market_structure"]})
        user = json.dumps({"report": {k: v for k, v in report.items()
                                      if k != "reasoning"},
                           "knowledge": {
                               "wins": [getattr(h, "text", "") for h in rag.get("wins", [])],
                               "losses": [getattr(h, "text", "") for h in rag.get("losses", [])],
                               "rules": [getattr(h, "text", "") for h in rag.get("rules", [])],
                           }}, default=str)
        try:
            out = chat(system=self.system, user=user, json_mode=True)
            return json.loads(out).get("reasoning", out)
        except Exception as e:                      # offline / no Ollama
            return f"[LLM unavailable: {e}] Deterministic verdict: {report['verdict']}"
