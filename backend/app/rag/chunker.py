from __future__ import annotations

from app.domain.enums import DocType


def chunk(text: str, doc_type: str, max_tokens: int = 500, overlap: int = 75):
    """Per-trade chunks for journals (don't fragment a setup); structure-aware
    for strategy docs; recursive for notes. Token count approximated by words."""
    if doc_type == DocType.JOURNAL.value:
        return [text.strip()]                       # one chunk per trade
    words = text.split()
    step = max_tokens - overlap
    return [" ".join(words[i:i + max_tokens])
            for i in range(0, len(words), step)] or [text]
