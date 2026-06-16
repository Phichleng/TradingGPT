from __future__ import annotations

import hashlib

from app.rag.chunker import chunk
from app.rag.embedder import embed


def ingest_document(store, *, doc_id, doc_type, text, metadata: dict):
    chunks = chunk(text, doc_type)
    ids = [hashlib.sha1(f"{doc_id}:{i}".encode()).hexdigest()
           for i in range(len(chunks))]
    payloads = [{**metadata, "doc_id": doc_id, "doc_type": doc_type,
                 "chunk_index": i, "text": c} for i, c in enumerate(chunks)]
    store.upsert(ids, embed(chunks), payloads)
    return len(chunks)
