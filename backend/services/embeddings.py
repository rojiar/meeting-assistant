import math
from typing import Sequence

import httpx

from backend.config import EMBEDDING_MODEL, GOOGLE_API_KEY
from backend.services.gemini_errors import raise_for_gemini_response


class EmbeddingService:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or GOOGLE_API_KEY
        self.model = EMBEDDING_MODEL

    async def embed(
        self, texts: Sequence[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not configured")

        vectors: list[list[float]] = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for text in texts:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent",
                    params={"key": self.api_key},
                    json={
                        "model": f"models/{self.model}",
                        "content": {"parts": [{"text": text}]},
                        "taskType": task_type,
                    },
                )
                raise_for_gemini_response(response)
                payload = response.json()
                embedding = payload.get("embedding", {}).get("values")
                if not embedding:
                    raise ValueError(f"Unexpected embedding response: {payload}")
                vectors.append(embedding)
        return vectors

    async def embed_one(
        self, text: str, task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[float]:
        return (await self.embed([text], task_type=task_type))[0]

    async def embed_query(self, text: str) -> list[float]:
        return await self.embed_one(text, task_type="RETRIEVAL_QUERY")


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
