"""
Document processing service.
Orchestrates the complete ingestion pipeline:
1. Parse PDF/DOCX
2. Hierarchical chunking
3. Generate embeddings
4. Index in Qdrant
5. Build Neo4j graph
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.domain.document import Document, DocumentStatus
from app.repositories.graph_repo import get_graph_repository
from app.repositories.vector_repo import get_vector_repository
from app.utils.chunking import HierarchicalChunker
from app.utils.document_parser import parse_document
from app.utils.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class DocumentProcessingError(Exception):
    """Custom exception for document processing errors."""

    pass


class DocumentProcessor:
    """
    Service for processing uploaded documents through the RAG pipeline.

    Pipeline stages:
    1. Parse: Extract text and structure
    2. Chunk: Create hierarchical chunks
    3. Embed: Generate embeddings
    4. Index: Store in Qdrant
    5. Graph: Build Neo4j knowledge graph
    """

    def __init__(self):
        """Initialize processor with required services."""
        self.embedding_service = get_embedding_service()
        self.vector_repo = get_vector_repository()
        self.graph_repo = get_graph_repository()
        self.chunker = HierarchicalChunker(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

    async def process_document(
        self,
        document_id: int,
        db: AsyncSession,
    ) -> None:
        """
        Process a document through the complete pipeline.

        Args:
            document_id: Database document ID
            db: Database session

        Raises:
            DocumentProcessingError: If processing fails
        """
        start_time = time.time()
        logger.info(f"Starting processing for document {document_id}")

        # Get document from database
        query = select(Document).where(Document.id == document_id)
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            raise DocumentProcessingError(f"Document {document_id} not found")

        try:
            # Update status to PROCESSING
            document.status = DocumentStatus.PROCESSING
            await db.commit()

            # Stage 1: Parse document
            logger.info(f"[1/5] Parsing document: {document.filename}")
            elements, metadata = parse_document(document.file_path)

            # Update document metadata
            document.title = metadata.get("title", document.filename)
            document.page_count = metadata.get("page_count", 0)
            document.file_type = metadata.get("file_type", "")
            await db.commit()

            logger.info(f"Parsed {len(elements)} elements from {document.filename}")

            # Stage 2: Chunk document
            logger.info("[2/5] Chunking document with hierarchical strategy")
            chunks = self.chunker.chunk_document(elements, document_id)

            document.chunk_count = len(chunks)
            await db.commit()

            logger.info(f"Created {len(chunks)} chunks")

            # Stage 3: Generate embeddings
            logger.info(f"[3/5] Generating embeddings for {len(chunks)} chunks")
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding_service.batch_encode_passages(
                chunk_texts,
                show_progress=True,
            )

            logger.info(f"Generated {len(embeddings)} embeddings")

            # Stage 4: Index in Qdrant
            logger.info("[4/5] Indexing chunks in Qdrant")

            # Ensure collection exists
            try:
                self.vector_repo.create_collection(recreate=False)
            except Exception as e:
                logger.warning(f"Collection may already exist: {e}")

            # Index chunks
            self.vector_repo.index_chunks(chunks, embeddings)

            logger.info(f"Indexed {len(chunks)} chunks in Qdrant")

            # Stage 5: Build knowledge graph
            logger.info("[5/5] Building knowledge graph in Neo4j")

            # Create document node
            self.graph_repo.create_document_node(
                document_id=document_id,
                filename=document.filename,
                metadata={
                    "title": document.title,
                    "page_count": document.page_count,
                },
            )

            # Create chunk nodes and hierarchy
            self.graph_repo.create_chunk_nodes(chunks)

            # Create references between chunks
            self.graph_repo.create_references(chunks)

            # Create entity nodes
            self.graph_repo.create_entity_nodes(chunks)

            logger.info("Knowledge graph construction completed")

            # Calculate processing time
            processing_time = time.time() - start_time

            # Update document status to COMPLETED
            document.status = DocumentStatus.COMPLETED
            document.processed_at = datetime.utcnow()
            document.processing_time = processing_time
            document.error_message = None

            await db.commit()

            logger.info(
                f"Document {document_id} processed successfully in {processing_time:.2f}s"
            )

        except Exception as e:
            # Update document status to FAILED
            error_message = str(e)
            logger.error(
                f"Document processing failed for {document_id}: {error_message}"
            )

            document.status = DocumentStatus.FAILED
            document.processing_error = error_message
            await db.commit()

            raise DocumentProcessingError(f"Processing failed: {error_message}") from e

    async def reprocess_document(
        self,
        document_id: int,
        db: AsyncSession,
    ) -> None:
        """
        Reprocess a document (deletes old data first).

        Args:
            document_id: Database document ID
            db: Database session
        """
        logger.info(f"Reprocessing document {document_id}")

        # Get document
        query = select(Document).where(Document.id == document_id)
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            raise DocumentProcessingError(f"Document {document_id} not found")

        try:
            # Delete old data
            logger.info("Deleting old data from Qdrant and Neo4j")

            # Delete from Qdrant
            try:
                self.vector_repo.delete_by_document(document_id)
            except Exception as e:
                logger.warning(f"Failed to delete from Qdrant: {e}")

            # Delete from Neo4j
            try:
                self.graph_repo.delete_document_graph(document_id)
            except Exception as e:
                logger.warning(f"Failed to delete from Neo4j: {e}")

            # Reset document metadata
            document.chunk_count = None
            document.entity_count = None
            document.processing_time = None
            document.processed_at = None
            document.error_message = None

            await db.commit()

            # Process document
            await self.process_document(document_id, db)

        except Exception as e:
            logger.error(f"Reprocessing failed for document {document_id}: {e}")
            raise

    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the processing services.

        Returns:
            Dictionary with service stats
        """
        stats = {
            "embedding_service": {
                "model": self.embedding_service.model_name,
                "device": self.embedding_service.device,
                "dimension": self.embedding_service.embedding_dimension,
            },
            "vector_database": {},
            "graph_database": {},
        }

        # Get Qdrant stats
        try:
            qdrant_info = self.vector_repo.get_collection_info()
            stats["vector_database"] = qdrant_info
        except Exception as e:
            logger.error(f"Failed to get Qdrant stats: {e}")
            stats["vector_database"]["error"] = str(e)

        # Get Neo4j stats
        try:
            graph_stats = self.graph_repo.get_graph_stats()
            stats["graph_database"] = graph_stats
        except Exception as e:
            logger.error(f"Failed to get Neo4j stats: {e}")
            stats["graph_database"]["error"] = str(e)

        return stats


# Global document processor instance (singleton)
_document_processor: Optional[DocumentProcessor] = None


def get_document_processor() -> DocumentProcessor:
    """
    Get or create global document processor instance.

    Returns:
        DocumentProcessor instance
    """
    global _document_processor

    if _document_processor is None:
        logger.info("Initializing global document processor")
        _document_processor = DocumentProcessor()

    return _document_processor
