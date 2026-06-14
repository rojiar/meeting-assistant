"""Vector storage via ChromaDB (embedded, local, no separate server)."""

from pathlib import Path

import chromadb
from chromadb.config import Settings

from backend.models.schemas import TranscriptChunk
from backend.services.embeddings import EmbeddingService

COLLECTION_NAME = "meeting_chunks"


class StoredChunk:
    def __init__(
        self,
        chunk_id: str,
        speaker: str,
        text: str,
        embedding: list[float] | None = None,
    ) -> None:
        self.chunk_id = chunk_id
        self.speaker = speaker
        self.text = text
        self.embedding = embedding


class VectorStore:
    """ChromaDB-backed store — replaces manual JSON + cosine loops."""

    def __init__(
        self,
        persist_dir: Path,
        embedder: EmbeddingService | None = None,
    ) -> None:
        self.persist_dir = persist_dir
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder or EmbeddingService()
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def _doc_id(self, meeting_id: str, chunk_id: str) -> str:
        return f"{meeting_id}:{chunk_id}"

    async def index_meeting(
        self,
        meeting_id: str,
        chunks: list[TranscriptChunk],
    ) -> None:
        if not chunks:
            self._collection.delete(where={"meeting_id": meeting_id})
            return

        embeddings = await self.embedder.embed([c.text for c in chunks])
        ids = [self._doc_id(meeting_id, c.chunk_id) for c in chunks]
        metadatas = [
            {
                "meeting_id": meeting_id,
                "chunk_id": c.chunk_id,
                "speaker": c.speaker,
            }
            for c in chunks
        ]
        documents = [c.text for c in chunks]

        # Replace vectors for this meeting
        self._collection.delete(where={"meeting_id": meeting_id})
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def load(self, meeting_id: str) -> list[StoredChunk]:
        """Load all chunks for a meeting (mainly for tests)."""
        result = self._collection.get(
            where={"meeting_id": meeting_id},
            include=["documents", "metadatas", "embeddings"],
        )
        chunks: list[StoredChunk] = []
        ids = result.get("ids") or []
        docs = result.get("documents") or []
        metas = result.get("metadatas") or []
        embs = result.get("embeddings")
        if embs is None:
            embs = []
        for i, _id in enumerate(ids):
            meta = metas[i] if i < len(metas) else {}
            chunks.append(
                StoredChunk(
                    chunk_id=meta.get("chunk_id", ""),
                    speaker=meta.get("speaker", ""),
                    text=docs[i] if i < len(docs) else "",
                    embedding=embs[i] if i < len(embs) else None,
                )
            )
        return chunks

    async def search(
        self,
        meeting_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[StoredChunk]:
        query_embedding = await self.embedder.embed_query(query)
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"meeting_id": meeting_id},
            include=["documents", "metadatas", "distances"],
        )

        chunks: list[StoredChunk] = []
        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]

        for i, _id in enumerate(ids):
            meta = metas[i] if i < len(metas) else {}
            chunks.append(
                StoredChunk(
                    chunk_id=meta.get("chunk_id", ""),
                    speaker=meta.get("speaker", ""),
                    text=docs[i] if i < len(docs) else "",
                )
            )
        return chunks

    def delete_meeting(self, meeting_id: str) -> None:
        self._collection.delete(where={"meeting_id": meeting_id})
