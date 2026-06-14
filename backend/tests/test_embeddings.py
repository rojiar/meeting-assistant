import math

import pytest

from backend.services.embeddings import EmbeddingService, cosine_similarity


class TestCosineSimilarity:
    def test_identical_vectors(self):
        vec = [1.0, 2.0, 3.0]
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_scaled_vectors_same_direction(self):
        a = [1.0, 2.0, 3.0]
        b = [2.0, 4.0, 6.0]
        assert cosine_similarity(a, b) == pytest.approx(1.0)

    def test_known_value(self):
        a = [1.0, 0.0]
        b = [1.0, 1.0]
        expected = 1 / math.sqrt(2)
        assert cosine_similarity(a, b) == pytest.approx(expected)


class TestEmbeddingServiceValidation:
    @pytest.mark.asyncio
    async def test_embed_raises_without_api_key(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("backend.services.embeddings.GOOGLE_API_KEY", "")
        service = EmbeddingService(api_key="")
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            await service.embed(["hi"])
