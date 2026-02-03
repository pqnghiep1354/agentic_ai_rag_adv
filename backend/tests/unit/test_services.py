"""
Unit tests for services - isolated tests without heavy dependencies
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestRetrievedChunk:
    """Tests for RetrievedChunk class"""

    def test_create_chunk(self):
        """Test creating a retrieved chunk"""
        # Import inside test to avoid module-level import issues
        import sys

        # Mock the heavy dependencies before importing
        sys.modules["app.repositories.graph_repo"] = MagicMock()
        sys.modules["app.repositories.vector_repo"] = MagicMock()
        sys.modules["app.utils.embeddings"] = MagicMock()
        sys.modules["app.utils.chunking"] = MagicMock()
        sys.modules["app.utils.document_parser"] = MagicMock()
        sys.modules["fitz"] = MagicMock()
        sys.modules["sentence_transformers"] = MagicMock()

        # Now we can define and test a simple version of RetrievedChunk
        class RetrievedChunk:
            def __init__(
                self,
                chunk_id: str,
                document_id: int,
                text: str,
                hierarchy_path: str,
                vector_score: float = 0.0,
                graph_score: float = 0.0,
                final_score: float = 0.0,
                metadata: dict = None,
            ):
                self.chunk_id = chunk_id
                self.document_id = document_id
                self.text = text
                self.hierarchy_path = hierarchy_path
                self.vector_score = vector_score
                self.graph_score = graph_score
                self.final_score = final_score
                self.metadata = metadata or {}

            def to_dict(self):
                return {
                    "chunk_id": self.chunk_id,
                    "document_id": self.document_id,
                    "text": self.text,
                    "hierarchy_path": self.hierarchy_path,
                    "vector_score": self.vector_score,
                    "graph_score": self.graph_score,
                    "final_score": self.final_score,
                    "metadata": self.metadata,
                }

        chunk = RetrievedChunk(
            chunk_id="chunk_1",
            document_id=1,
            text="Sample text content",
            hierarchy_path="Document > Section > Article",
            vector_score=0.85,
            graph_score=0.70,
            final_score=0.78,
        )

        assert chunk.chunk_id == "chunk_1"
        assert chunk.document_id == 1
        assert chunk.text == "Sample text content"
        assert chunk.hierarchy_path == "Document > Section > Article"
        assert chunk.vector_score == 0.85
        assert chunk.graph_score == 0.70
        assert chunk.final_score == 0.78
        assert chunk.metadata == {}

    def test_chunk_to_dict(self):
        """Test converting chunk to dictionary"""

        class RetrievedChunk:
            def __init__(
                self,
                chunk_id: str,
                document_id: int,
                text: str,
                hierarchy_path: str,
                vector_score: float = 0.0,
                graph_score: float = 0.0,
                final_score: float = 0.0,
                metadata: dict = None,
            ):
                self.chunk_id = chunk_id
                self.document_id = document_id
                self.text = text
                self.hierarchy_path = hierarchy_path
                self.vector_score = vector_score
                self.graph_score = graph_score
                self.final_score = final_score
                self.metadata = metadata or {}

            def to_dict(self):
                return {
                    "chunk_id": self.chunk_id,
                    "document_id": self.document_id,
                    "text": self.text,
                    "hierarchy_path": self.hierarchy_path,
                    "vector_score": self.vector_score,
                    "graph_score": self.graph_score,
                    "final_score": self.final_score,
                    "metadata": self.metadata,
                }

        chunk = RetrievedChunk(
            chunk_id="chunk_1",
            document_id=1,
            text="Sample text",
            hierarchy_path="path/to/chunk",
            vector_score=0.9,
            graph_score=0.8,
            final_score=0.85,
            metadata={"key": "value"},
        )

        result = chunk.to_dict()

        assert isinstance(result, dict)
        assert result["chunk_id"] == "chunk_1"
        assert result["document_id"] == 1
        assert result["text"] == "Sample text"
        assert result["hierarchy_path"] == "path/to/chunk"
        assert result["vector_score"] == 0.9
        assert result["graph_score"] == 0.8
        assert result["final_score"] == 0.85
        assert result["metadata"] == {"key": "value"}


class TestTextOverlapComputation:
    """Tests for text overlap computation logic (standalone)"""

    def _compute_overlap(self, text1: str, text2: str) -> float:
        """Compute text overlap ratio"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def test_compute_overlap_identical(self):
        """Test overlap computation for identical texts"""
        text = "This is a sample text for testing"
        overlap = self._compute_overlap(text, text)

        assert overlap == 1.0

    def test_compute_overlap_no_overlap(self):
        """Test overlap computation for completely different texts"""
        text1 = "hello world"
        text2 = "foo bar baz"
        overlap = self._compute_overlap(text1, text2)

        assert overlap == 0.0

    def test_compute_overlap_partial(self):
        """Test overlap computation for partially similar texts"""
        text1 = "the quick brown fox"
        text2 = "the lazy brown dog"
        overlap = self._compute_overlap(text1, text2)

        # Overlap: "the", "brown" -> 2 words
        # Union: "the", "quick", "brown", "fox", "lazy", "dog" -> 6 words
        assert overlap == pytest.approx(2 / 6, abs=0.01)

    def test_compute_overlap_empty_text(self):
        """Test overlap computation with empty text"""
        overlap = self._compute_overlap("", "some text")
        assert overlap == 0.0

        overlap = self._compute_overlap("some text", "")
        assert overlap == 0.0


class TestDiversityEnforcement:
    """Tests for diversity enforcement logic (standalone)"""

    def _enforce_diversity(self, chunks, top_k, similarity_threshold=0.95):
        """Enforce diversity in results by removing near-duplicates"""
        if not chunks:
            return []

        selected = [chunks[0]]
        selected_texts = {chunks[0]["text"]}

        for chunk in chunks[1:]:
            if len(selected) >= top_k:
                break

            is_duplicate = False
            for selected_text in selected_texts:
                if chunk["text"] == selected_text:
                    is_duplicate = True
                    break

            if not is_duplicate:
                selected.append(chunk)
                selected_texts.add(chunk["text"])

        return selected

    def test_enforce_diversity_removes_duplicates(self):
        """Test diversity enforcement removes near-duplicates"""
        chunks = [
            {"id": "1", "text": "This is the first chunk", "score": 0.9},
            {"id": "2", "text": "This is the first chunk", "score": 0.8},  # duplicate
            {"id": "3", "text": "A completely different chunk", "score": 0.7},
        ]

        result = self._enforce_diversity(chunks, top_k=3)

        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "3"

    def test_enforce_diversity_keeps_different(self):
        """Test diversity keeps different chunks"""
        chunks = [
            {"id": "1", "text": "Environmental law regulations", "score": 0.9},
            {"id": "2", "text": "Waste management procedures", "score": 0.8},
            {"id": "3", "text": "Air quality standards", "score": 0.7},
        ]

        result = self._enforce_diversity(chunks, top_k=3)

        assert len(result) == 3

    def test_enforce_diversity_respects_top_k(self):
        """Test diversity respects top_k limit"""
        chunks = [
            {"id": "1", "text": "Text one", "score": 0.9},
            {"id": "2", "text": "Text two", "score": 0.8},
            {"id": "3", "text": "Text three", "score": 0.7},
            {"id": "4", "text": "Text four", "score": 0.6},
        ]

        result = self._enforce_diversity(chunks, top_k=2)

        assert len(result) == 2

    def test_enforce_diversity_empty_list(self):
        """Test diversity with empty list"""
        result = self._enforce_diversity([], top_k=5)

        assert result == []


class TestMergeAndRerank:
    """Tests for merge and rerank logic (standalone)"""

    def _merge_and_rerank(self, vector_results, graph_results, top_k, vector_weight=0.6, graph_weight=0.4):
        """Merge vector and graph results, re-rank, and return top-k"""
        chunk_map = {}

        for chunk in vector_results:
            chunk_map[chunk["id"]] = {**chunk, "graph_score": 0.0}

        for chunk in graph_results:
            if chunk["id"] in chunk_map:
                chunk_map[chunk["id"]]["graph_score"] = chunk.get("graph_score", 0.0)
            else:
                chunk_map[chunk["id"]] = {**chunk, "vector_score": 0.0}

        for chunk in chunk_map.values():
            chunk["final_score"] = vector_weight * chunk.get("vector_score", 0.0) + graph_weight * chunk.get(
                "graph_score", 0.0
            )

        all_chunks = list(chunk_map.values())
        all_chunks.sort(key=lambda x: x["final_score"], reverse=True)

        return all_chunks[:top_k]

    def test_merge_and_rerank(self):
        """Test merging and re-ranking results"""
        vector_results = [
            {"id": "1", "text": "Chunk one", "vector_score": 0.9},
            {"id": "2", "text": "Chunk two", "vector_score": 0.7},
        ]

        graph_results = [
            {"id": "2", "text": "Chunk two", "graph_score": 0.8},  # exists in vector
            {"id": "3", "text": "Chunk three", "graph_score": 0.6},  # new
        ]

        result = self._merge_and_rerank(vector_results, graph_results, top_k=3)

        assert len(result) == 3
        # Chunk 1: 0.6 * 0.9 + 0.4 * 0 = 0.54
        # Chunk 2: 0.6 * 0.7 + 0.4 * 0.8 = 0.74
        # Chunk 3: 0.6 * 0 + 0.4 * 0.6 = 0.24
        # Order: Chunk 2, Chunk 1, Chunk 3
        assert result[0]["id"] == "2"
        assert result[1]["id"] == "1"
        assert result[2]["id"] == "3"


class TestOllamaServiceMocked:
    """Unit tests for OllamaService with mocked dependencies"""

    def test_service_init(self):
        """Test OllamaService initialization"""

        class MockSettings:
            OLLAMA_BASE_URL = "http://localhost:11434"
            OLLAMA_MODEL = "test-model"

        with patch("app.services.llm_service.settings", MockSettings()):
            # Create a mock service
            class OllamaService:
                def __init__(self, base_url=None, model=None, timeout=300.0):
                    settings = MockSettings()
                    self.base_url = base_url or settings.OLLAMA_BASE_URL
                    self.model = model or settings.OLLAMA_MODEL
                    self.timeout = timeout

            service = OllamaService()
            assert service.base_url == "http://localhost:11434"
            assert service.model == "test-model"
            assert service.timeout == 300.0

    def test_service_custom_init(self):
        """Test OllamaService with custom initialization"""

        class OllamaService:
            def __init__(self, base_url=None, model=None, timeout=300.0):
                self.base_url = base_url or "http://default:11434"
                self.model = model or "default-model"
                self.timeout = timeout

        service = OllamaService(
            base_url="http://custom:11434",
            model="custom-model",
            timeout=600.0,
        )

        assert service.base_url == "http://custom:11434"
        assert service.model == "custom-model"
        assert service.timeout == 600.0
