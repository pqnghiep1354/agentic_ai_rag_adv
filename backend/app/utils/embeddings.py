"""
Embedding generation utilities using Multilingual-E5-Large.
Handles text encoding for semantic search.
"""

import logging
from typing import List, Optional, Union

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings using Multilingual-E5-Large model.

    E5 models require specific instruction prefixes:
    - "passage: " for documents/chunks to be indexed
    - "query: " for search queries
    """

    def __init__(
        self,
        model_name: str = settings.EMBEDDING_MODEL,
        device: Optional[str] = None,
        batch_size: int = settings.EMBEDDING_BATCH_SIZE,
    ):
        """
        Initialize embedding service.

        Args:
            model_name: HuggingFace model name
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
            batch_size: Batch size for encoding
        """
        self.model_name = model_name
        self.batch_size = batch_size

        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Initializing embedding model: {model_name} on {self.device}")

        # Load model
        try:
            self.model = SentenceTransformer(model_name, device=self.device)
            self.embedding_dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Embedding dimension: {self.embedding_dimension}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def encode_passages(
        self,
        texts: Union[str, List[str]],
        normalize: bool = True,
        show_progress: bool = False,
    ) -> np.ndarray:
        """
        Encode passages/documents for indexing.

        Args:
            texts: Single text or list of texts
            normalize: Whether to normalize embeddings (recommended for cosine similarity)
            show_progress: Show progress bar

        Returns:
            Numpy array of embeddings (shape: [num_texts, embedding_dim])
        """
        if isinstance(texts, str):
            texts = [texts]

        # Add E5 passage prefix
        prefixed_texts = [f"passage: {text}" for text in texts]

        logger.debug(f"Encoding {len(texts)} passages")

        try:
            embeddings = self.model.encode(
                prefixed_texts,
                batch_size=self.batch_size,
                normalize_embeddings=normalize,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
            )

            logger.debug(f"Generated embeddings shape: {embeddings.shape}")
            return embeddings

        except Exception as e:
            logger.error(f"Failed to encode passages: {e}")
            raise

    def encode_query(
        self,
        query: str,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Encode a search query.

        Args:
            query: Search query text
            normalize: Whether to normalize embedding

        Returns:
            Numpy array embedding (shape: [embedding_dim])
        """
        # Add E5 query prefix
        prefixed_query = f"query: {query}"

        logger.debug(f"Encoding query: {query[:50]}...")

        try:
            embedding = self.model.encode(
                prefixed_query,
                normalize_embeddings=normalize,
                convert_to_numpy=True,
            )

            logger.debug(f"Generated query embedding shape: {embedding.shape}")
            return embedding

        except Exception as e:
            logger.error(f"Failed to encode query: {e}")
            raise

    def compute_similarity(
        self,
        query_embedding: np.ndarray,
        passage_embeddings: np.ndarray,
    ) -> np.ndarray:
        """
        Compute cosine similarity between query and passages.

        Args:
            query_embedding: Query embedding (1D array)
            passage_embeddings: Passage embeddings (2D array)

        Returns:
            Similarity scores (1D array)
        """
        # Ensure 2D arrays
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        if passage_embeddings.ndim == 1:
            passage_embeddings = passage_embeddings.reshape(1, -1)

        # Compute cosine similarity
        similarity = np.dot(passage_embeddings, query_embedding.T).flatten()

        return similarity

    def batch_encode_passages(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        normalize: bool = True,
        show_progress: bool = True,
    ) -> List[np.ndarray]:
        """
        Encode passages in batches to avoid memory issues.

        Args:
            texts: List of texts to encode
            batch_size: Batch size (uses default if None)
            normalize: Whether to normalize embeddings
            show_progress: Show progress bar

        Returns:
            List of embeddings
        """
        batch_size = batch_size or self.batch_size

        all_embeddings = []

        logger.info(f"Encoding {len(texts)} passages in batches of {batch_size}")

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_embeddings = self.encode_passages(
                batch_texts,
                normalize=normalize,
                show_progress=show_progress and i == 0,  # Show progress only for first batch
            )
            all_embeddings.extend(batch_embeddings)

            if show_progress:
                logger.info(f"Processed {min(i + batch_size, len(texts))}/{len(texts)} passages")

        return all_embeddings

    def get_embedding_dimension(self) -> int:
        """Get the embedding dimension of the model."""
        return self.embedding_dimension

    def get_device(self) -> str:
        """Get the device being used."""
        return self.device


# Global embedding service instance (singleton)
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get or create global embedding service instance.

    Returns:
        EmbeddingService instance
    """
    global _embedding_service

    if _embedding_service is None:
        logger.info("Initializing global embedding service")
        _embedding_service = EmbeddingService()

    return _embedding_service


def encode_text_for_search(text: str) -> np.ndarray:
    """
    Convenience function to encode text for semantic search.

    Args:
        text: Text to encode

    Returns:
        Embedding vector
    """
    service = get_embedding_service()
    return service.encode_passages(text, normalize=True)[0]


def encode_query_for_search(query: str) -> np.ndarray:
    """
    Convenience function to encode query for semantic search.

    Args:
        query: Query text

    Returns:
        Query embedding vector
    """
    service = get_embedding_service()
    return service.encode_query(query, normalize=True)
