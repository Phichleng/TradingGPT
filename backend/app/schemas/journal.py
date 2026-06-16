from __future__ import annotations

from pydantic import BaseModel


class JournalIn(BaseModel):
    market: str
    direction: str
    strategy: str
    entry_price: float
    exit_price: float | None = None
    rr_realized: float | None = None
    outcome: str | None = None
    setup_notes: str = ""
    mistakes: str = ""
