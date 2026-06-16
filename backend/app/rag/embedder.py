from __future__ import annotations

# Phase 1: bge-large-en-v1.5 via sentence-transformers (local, no API cost).
# Kept lazy so the package imports without the heavy dep installed.
_model = None


def _load():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("BAAI/bge-large-en-v1.5")
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    return _load().encode(texts, normalize_embeddings=True).tolist()
