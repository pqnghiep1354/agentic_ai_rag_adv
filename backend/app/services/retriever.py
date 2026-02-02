"""
Hybrid retriever combining vector search and graph traversal
"""
import logging
from typing import List, Dict, Any, Optional
from ..repositories.vector_repo import VectorRepository
from ..repositories.graph_repo import GraphRepository
from ..utils.embeddings import EmbeddingService
from ..core.config import settings

logger = logging.getLogger(__name__)


class RetrievedChunk:
    """
    Retrieved chunk with metadata and relevance score
    """

    def __init__(
        self,
        chunk_id: str,
        document_id: int,
        text: str,
        hierarchy_path: str,
        vector_score: float = 0.0,
        graph_score: float = 0.0,
        final_score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.text = text
        self.hierarchy_path = hierarchy_path
        self.vector_score = vector_score
        self.graph_score = graph_score
        self.final_score = final_score
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "text": self.text,
            "hierarchy_path": self.hierarchy_path,
            "vector_score": self.vector_score,
            "graph_score": self.graph_score,
            "final_score": self.final_score,
            "metadata": self.metadata
        }


class HybridRetriever:
    """
    Hybrid retrieval combining:
    1. Vector search (dense + BM25) via Qdrant
    2. Graph traversal (multi-hop) via Neo4j
    3. Re-ranking and fusion
    """

    def __init__(
        self,
        vector_repo: VectorRepository,
        graph_repo: GraphRepository,
        embedding_service: EmbeddingService,
        top_k: int = None,
        graph_depth: int = None,
        vector_weight: float = 0.6,
        graph_weight: float = 0.4
    ):
        self.vector_repo = vector_repo
        self.graph_repo = graph_repo
        self.embedding_service = embedding_service
        self.top_k = top_k or settings.TOP_K_RETRIEVAL
        self.graph_depth = graph_depth or settings.GRAPH_TRAVERSAL_DEPTH
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        enable_graph: bool = True
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant chunks using hybrid approach

        Args:
            query: Search query
            top_k: Number of chunks to retrieve (default: settings.TOP_K_RETRIEVAL)
            filters: Optional filters for vector search
            enable_graph: Whether to enable graph traversal

        Returns:
            List of retrieved chunks sorted by relevance
        """
        k = top_k or self.top_k

        try:
            # Step 1: Vector search
            logger.info(f"Starting vector search for query: {query[:50]}...")
            vector_results = await self._vector_search(query, k * 2, filters)

            if not vector_results:
                logger.warning("No vector search results found")
                return []

            logger.info(f"Vector search returned {len(vector_results)} results")

            # Step 2: Graph expansion (if enabled)
            if enable_graph and vector_results:
                logger.info("Starting graph traversal")
                graph_results = await self._graph_traverse(vector_results)
                logger.info(f"Graph traversal returned {len(graph_results)} additional chunks")
            else:
                graph_results = []

            # Step 3: Merge and re-rank
            logger.info("Merging and re-ranking results")
            final_results = self._merge_and_rerank(
                vector_results,
                graph_results,
                k
            )

            logger.info(f"Final retrieval: {len(final_results)} chunks")
            return final_results

        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            raise

    async def _vector_search(
        self,
        query: str,
        limit: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievedChunk]:
        """
        Perform vector search using Qdrant

        Args:
            query: Search query
            limit: Number of results
            filters: Optional filters

        Returns:
            List of retrieved chunks with vector scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.encode_query(query)

            # Search Qdrant
            results = self.vector_repo.search(
                query_vector=query_embedding.tolist(),
                limit=limit,
                filters=filters
            )

            # Convert to RetrievedChunk objects
            chunks = []
            for result in results:
                payload = result.payload
                chunks.append(RetrievedChunk(
                    chunk_id=payload.get("chunk_id"),
                    document_id=payload.get("document_id"),
                    text=payload.get("text"),
                    hierarchy_path=payload.get("hierarchy_path", ""),
                    vector_score=result.score,
                    graph_score=0.0,
                    final_score=result.score,
                    metadata={
                        "page_number": payload.get("page_number"),
                        "section_title": payload.get("section_title"),
                        "article_number": payload.get("article_number"),
                        "document_title": payload.get("document_title")
                    }
                ))

            return chunks

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            raise

    async def _graph_traverse(
        self,
        seed_chunks: List[RetrievedChunk]
    ) -> List[RetrievedChunk]:
        """
        Traverse knowledge graph from seed chunks

        Args:
            seed_chunks: Starting chunks from vector search

        Returns:
            List of related chunks found via graph
        """
        try:
            # Extract chunk IDs
            seed_ids = [chunk.chunk_id for chunk in seed_chunks]

            # Find related chunks via graph traversal
            related = self.graph_repo.find_related_chunks(
                chunk_ids=seed_ids,
                max_depth=self.graph_depth,
                max_results=50
            )

            # Convert to RetrievedChunk objects
            chunks = []
            for item in related:
                chunks.append(RetrievedChunk(
                    chunk_id=item.get("chunk_id"),
                    document_id=item.get("document_id"),
                    text=item.get("text"),
                    hierarchy_path=item.get("hierarchy_path", ""),
                    vector_score=0.0,
                    graph_score=item.get("path_score", 0.0),
                    final_score=item.get("path_score", 0.0),
                    metadata={
                        "page_number": item.get("page_number"),
                        "section_title": item.get("section_title"),
                        "article_number": item.get("article_number"),
                        "relationship_type": item.get("relationship_type")
                    }
                ))

            return chunks

        except Exception as e:
            logger.error(f"Graph traversal error: {e}")
            raise

    def _merge_and_rerank(
        self,
        vector_results: List[RetrievedChunk],
        graph_results: List[RetrievedChunk],
        top_k: int
    ) -> List[RetrievedChunk]:
        """
        Merge vector and graph results, re-rank, and return top-k

        Args:
            vector_results: Results from vector search
            graph_results: Results from graph traversal
            top_k: Number of top results to return

        Returns:
            Merged and re-ranked chunks
        """
        try:
            # Create chunk_id -> chunk mapping
            chunk_map: Dict[str, RetrievedChunk] = {}

            # Add vector results
            for chunk in vector_results:
                chunk_map[chunk.chunk_id] = chunk

            # Merge graph results
            for chunk in graph_results:
                if chunk.chunk_id in chunk_map:
                    # Update existing chunk
                    existing = chunk_map[chunk.chunk_id]
                    existing.graph_score = chunk.graph_score
                else:
                    # Add new chunk
                    chunk_map[chunk.chunk_id] = chunk

            # Compute final scores using weighted fusion
            for chunk in chunk_map.values():
                chunk.final_score = (
                    self.vector_weight * chunk.vector_score +
                    self.graph_weight * chunk.graph_score
                )

            # Sort by final score
            all_chunks = list(chunk_map.values())
            all_chunks.sort(key=lambda x: x.final_score, reverse=True)

            # Return top-k with diversity
            final_chunks = self._enforce_diversity(all_chunks, top_k)

            return final_chunks

        except Exception as e:
            logger.error(f"Merge and rerank error: {e}")
            raise

    def _enforce_diversity(
        self,
        chunks: List[RetrievedChunk],
        top_k: int,
        similarity_threshold: float = 0.95
    ) -> List[RetrievedChunk]:
        """
        Enforce diversity in results by removing near-duplicates

        Args:
            chunks: Sorted chunks
            top_k: Number of chunks to return
            similarity_threshold: Threshold for duplicate detection

        Returns:
            Diverse set of chunks
        """
        if not chunks:
            return []

        selected = [chunks[0]]
        selected_texts = {chunks[0].text}

        for chunk in chunks[1:]:
            if len(selected) >= top_k:
                break

            # Simple duplicate detection based on text overlap
            is_duplicate = False
            for selected_text in selected_texts:
                # Check text similarity (simple approach)
                if chunk.text == selected_text:
                    is_duplicate = True
                    break

                # Check if texts are very similar (>95% overlap)
                overlap = self._compute_overlap(chunk.text, selected_text)
                if overlap > similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                selected.append(chunk)
                selected_texts.add(chunk.text)

        return selected

    def _compute_overlap(self, text1: str, text2: str) -> float:
        """
        Compute text overlap ratio

        Args:
            text1: First text
            text2: Second text

        Returns:
            Overlap ratio (0.0 to 1.0)
        """
        # Simple word-level overlap
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0


# Global singleton instance
_retriever: Optional[HybridRetriever] = None


def get_retriever() -> HybridRetriever:
    """
    Get global retriever instance

    Returns:
        HybridRetriever instance
    """
    global _retriever
    if _retriever is None:
        from ..repositories.vector_repo import get_vector_repository
        from ..repositories.graph_repo import get_graph_repository
        from ..utils.embeddings import get_embedding_service

        _retriever = HybridRetriever(
            vector_repo=get_vector_repository(),
            graph_repo=get_graph_repository(),
            embedding_service=get_embedding_service()
        )
    return _retriever
