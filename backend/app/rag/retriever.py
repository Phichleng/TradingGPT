from __future__ import annotations


class Retriever:
    def __init__(self, store):
        self.store = store

    def retrieve(self, *, market, strategy, regime, structure_summary, k=6):
        q = (f"{market} {strategy} setup in {regime['regime']} regime; "
             f"{structure_summary['trend']} trend, "
             f"structure {structure_summary['structure_status']}")
        try:
            wins = self.store.search(q, 3, {"market": market, "strategy": strategy,
                                            "outcome": "win"})
            losses = self.store.search(q, 2, {"market": market, "strategy": strategy,
                                              "outcome": "loss"})
            rules = self.store.search(q, 2, {"doc_type": "strategy",
                                             "strategy": strategy})
        except Exception:
            wins = losses = rules = []
        return {"wins": wins, "losses": losses, "rules": rules}
