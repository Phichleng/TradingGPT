from __future__ import annotations


class ChromaStore:
    """Adapter over ChromaDB (Phase 1). Swap for QdrantStore in prod — both
    satisfy the VectorStore protocol so nothing else changes."""

    def __init__(self, path: str = "./vector_db", collection: str = "knowledge"):
        self.path, self.collection_name = path, collection
        self._col = None

    def _col_or_init(self):
        if self._col is None:
            import chromadb
            client = chromadb.PersistentClient(path=self.path)
            self._col = client.get_or_create_collection(self.collection_name)
        return self._col

    def upsert(self, ids, vectors, payloads):
        self._col_or_init().upsert(
            ids=ids, embeddings=vectors, metadatas=payloads,
            documents=[p.get("text", "") for p in payloads])

    def search(self, query, k=6, filters=None):
        from app.rag.embedder import embed
        res = self._col_or_init().query(
            query_embeddings=embed([query]), n_results=k, where=filters or None)
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        return [type("Hit", (), {"text": d, "meta": m})()
                for d, m in zip(docs, metas)]
