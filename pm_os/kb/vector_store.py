"""
Vector store backed by ChromaDB for semantic search across KB documents.

Collections:
  industry_context  — benchmarks, patterns, best practices
  company_context   — company-specific docs, analyses
  decision_history  — past decisions with outcomes
  competitive_intel — competitor moves, market data
"""

from pathlib import Path

import chromadb
from chromadb.config import Settings

from pm_os.kb.schemas import KBDocument, VectorCollection

_DEFAULT_PERSIST = Path(__file__).resolve().parent / "chroma_data"


class VectorStore:
    """ChromaDB wrapper with typed collections."""

    def __init__(self, persist_dir: str | Path | None = None):
        self.persist_dir = str(persist_dir or _DEFAULT_PERSIST)
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collections: dict[str, chromadb.Collection] = {}

    def _get_collection(self, name: VectorCollection) -> chromadb.Collection:
        key = name.value
        if key not in self._collections:
            self._collections[key] = self.client.get_or_create_collection(
                name=key,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[key]

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add_document(self, doc: KBDocument) -> None:
        """Add a single document to its collection."""
        col = self._get_collection(doc.collection)
        col.upsert(
            ids=[doc.id],
            documents=[doc.text],
            metadatas=[doc.metadata],
        )

    def add_documents(self, docs: list[KBDocument]) -> None:
        """Batch-add documents, grouped by collection."""
        by_collection: dict[VectorCollection, list[KBDocument]] = {}
        for doc in docs:
            by_collection.setdefault(doc.collection, []).append(doc)

        for collection, batch in by_collection.items():
            col = self._get_collection(collection)
            col.upsert(
                ids=[d.id for d in batch],
                documents=[d.text for d in batch],
                metadatas=[d.metadata for d in batch],
            )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def query(
        self,
        collection: VectorCollection,
        query_text: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        """
        Semantic search within a collection.

        Returns list of dicts with keys: id, text, metadata, distance.
        """
        col = self._get_collection(collection)
        kwargs: dict = {
            "query_texts": [query_text],
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where

        results = col.query(**kwargs)

        docs = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            docs.append({
                "id": doc_id,
                "text": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "distance": distances[i] if i < len(distances) else 1.0,
            })
        return docs

    def query_multiple(
        self,
        collections: list[VectorCollection],
        query_text: str,
        n_results: int = 3,
    ) -> list[dict]:
        """Search across multiple collections, merge and sort by distance."""
        all_results = []
        for col in collections:
            results = self.query(col, query_text, n_results=n_results)
            for r in results:
                r["collection"] = col.value
            all_results.extend(results)

        all_results.sort(key=lambda r: r["distance"])
        return all_results

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    def count(self, collection: VectorCollection) -> int:
        col = self._get_collection(collection)
        return col.count()

    def delete_collection(self, collection: VectorCollection) -> None:
        self.client.delete_collection(collection.value)
        self._collections.pop(collection.value, None)

    def reset(self) -> None:
        """Delete all collections."""
        for col_enum in VectorCollection:
            try:
                self.client.delete_collection(col_enum.value)
            except ValueError:
                pass
        self._collections.clear()
