from __future__ import annotations

from fastapi import APIRouter

from app.schemas.journal import JournalIn

router = APIRouter(tags=["journals"])


@router.post("/journals")
def create_journal(j: JournalIn):
    # TODO: persist to journals table, then trigger RAG re-ingest of this trade.
    return {"status": "created", "journal": j.model_dump()}


@router.get("/journals")
def list_journals(market: str | None = None):
    return {"items": [], "market": market}
