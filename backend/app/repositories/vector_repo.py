"""
Qdrant vector database repository.
Handles vector storage, search, and hybrid retrieval.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import settings
from app.utils.chunking import Chunk

logger = logging.getLogger(__name__)


class VectorRepository:
    """
    Repository for Qdrant vector database operations.

    Supports:
    - Dense vector search (semantic similarity)
    - Sparse vector search (BM25 keyword matching) - TODO
    - Hybrid search combining both
    - Filtering by metadata
    """

    def __init__(
        self,
        url: str = settings.QDRANT_URL,
        collection_name: str = settings.QDRANT_COLLECTION_CHUNKS,
    ):
        """
        Initialize Qdrant client.

        Args:
            url: Qdrant server URL
            collection_name: Name of the collection to use
        """
        self.collection_name = collection_name
        logger.info(f"Connecting to Qdrant at {url}")

        try:
            self.client = QdrantClient(url=url)
            logger.info("Connected to Qdrant successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    def create_collection(
        self,
        vector_size: int = settings.EMBEDDING_DIMENSION,
        distance: Distance = Distance.COSINE,
        recreate: bool = False,
    ) -> None:
        """
        Create Qdrant collection if it doesn't exist.

        Args:
            vector_size: Dimension of embeddings
            distance: Distance metric (COSINE, EUCLID, DOT)
            recreate: Whether to recreate if collection exists
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_exists = any(col.name == self.collection_name for col in collections)

            if collection_exists:
                if recreate:
                    logger.info(f"Recreating collection: {self.collection_name}")
                    self.client.delete_collection(self.collection_name)
                else:
                    logger.info(f"Collection already exists: {self.collection_name}")
                    return

            # Create collection
            logger.info(f"Creating collection: {self.collection_name} with dimension {vector_size}")

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance,
                ),
            )

            # Create indexes for filtering
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="document_id",
                field_schema=models.PayloadSchemaType.INTEGER,
            )

            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="hierarchy_level",
                field_schema=models.PayloadSchemaType.INTEGER,
            )

            logger.info(f"Collection created successfully: {self.collection_name}")

        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise

    def index_chunks(
        self,
        chunks: List[Chunk],
        embeddings: List[np.ndarray],
        batch_size: int = 100,
    ) -> None:
        """
        Index chunks with their embeddings in Qdrant.

        Args:
            chunks: List of Chunk objects
            embeddings: List of embedding vectors
            batch_size: Batch size for uploading
        """
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunks and embeddings length mismatch: {len(chunks)} vs {len(embeddings)}")

        logger.info(f"Indexing {len(chunks)} chunks in collection {self.collection_name}")

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            # Create point
            point = PointStruct(
                id=str(uuid.uuid4()),  # Generate UUID for each point
                vector=(embedding.tolist() if isinstance(embedding, np.ndarray) else embedding),
                payload={
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "text": chunk.text,
                    "page_number": chunk.page_number,
                    "hierarchy_level": chunk.hierarchy_level,
                    "hierarchy_path": chunk.hierarchy_path,
                    "parent_chunk_id": chunk.parent_chunk_id,
                    **chunk.metadata,
                },
            )
            points.append(point)

        # Upload in batches
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                )
                logger.debug(f"Uploaded batch {i // batch_size + 1}/{(len(points) - 1) // batch_size + 1}")
            except Exception as e:
                logger.error(f"Failed to upload batch: {e}")
                raise

        logger.info(f"Successfully indexed {len(chunks)} chunks")

    def search(
        self,
        query_vector: np.ndarray,
        limit: int = 20,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using dense vector search.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_conditions: Optional filters (e.g., {"document_id": 123})

        Returns:
            List of search results with scores and payloads
        """
        logger.debug(f"Searching with limit={limit}, score_threshold={score_threshold}")

        # Build filter if provided
        query_filter = None
        if filter_conditions:
            must_conditions = []
            for key, value in filter_conditions.items():
                must_conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value),
                    )
                )
            query_filter = Filter(must=must_conditions)

        try:
            # Convert numpy array to list
            if isinstance(query_vector, np.ndarray):
                query_vector = query_vector.tolist()

            # Search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
            )

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "id": result.id,
                        "score": result.score,
                        "chunk_id": result.payload.get("chunk_id"),
                        "document_id": result.payload.get("document_id"),
                        "text": result.payload.get("text"),
                        "page_number": result.payload.get("page_number"),
                        "hierarchy_level": result.payload.get("hierarchy_level"),
                        "hierarchy_path": result.payload.get("hierarchy_path"),
                        "metadata": {
                            k: v
                            for k, v in result.payload.items()
                            if k
                            not in [
                                "chunk_id",
                                "document_id",
                                "text",
                                "page_number",
                                "hierarchy_level",
                                "hierarchy_path",
                            ]
                        },
                    }
                )

            logger.debug(f"Found {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def delete_by_document(self, document_id: int) -> None:
        """
        Delete all chunks belonging to a document.

        Args:
            document_id: Document ID to delete
        """
        logger.info(f"Deleting chunks for document_id={document_id}")

        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=Filter(
                        must=[
                            FieldCondition(
                                key="document_id",
                                match=MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
            logger.info(f"Deleted chunks for document_id={document_id}")

        except Exception as e:
            logger.error(f"Failed to delete chunks: {e}")
            raise

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection.

        Returns:
            Dictionary with collection stats
        """
        try:
            collection_info = self.client.get_collection(self.collection_name)

            return {
                "name": self.collection_name,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
                "config": {
                    "distance": collection_info.config.params.vectors.distance,
                    "size": collection_info.config.params.vectors.size,
                },
            }

        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise

    def hybrid_search(
        self,
        query_vector: np.ndarray,
        query_text: str,
        limit: int = 20,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining dense (semantic) and sparse (keyword) search.

        Note: Sparse search requires separate configuration in Qdrant.
        This is a simplified version using only dense search.
        TODO: Implement proper BM25 sparse search.

        Args:
            query_vector: Dense query vector
            query_text: Query text (for sparse search)
            limit: Maximum number of results
            dense_weight: Weight for dense search (0-1)
            sparse_weight: Weight for sparse search (0-1)
            filter_conditions: Optional filters

        Returns:
            List of search results
        """
        # For now, just use dense search
        # TODO: Add sparse search when configured
        logger.debug("Hybrid search (using dense only for now)")

        return self.search(
            query_vector=query_vector,
            limit=limit,
            filter_conditions=filter_conditions,
        )


# Global vector repository instance (singleton)
_vector_repo: Optional[VectorRepository] = None


def get_vector_repository() -> VectorRepository:
    """
    Get or create global vector repository instance.

    Returns:
        VectorRepository instance
    """
    global _vector_repo

    if _vector_repo is None:
        logger.info("Initializing global vector repository")
        _vector_repo = VectorRepository()

    return _vector_repo
