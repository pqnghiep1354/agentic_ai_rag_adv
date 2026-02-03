"""
RAG service orchestrating retrieval and generation
"""

import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from ..core.config import settings
from ..utils.prompts import LEGAL_SYSTEM_PROMPT, build_rag_prompt
from .llm_service import OllamaService, get_ollama_service
from .retriever import HybridRetriever, RetrievedChunk, get_retriever

logger = logging.getLogger(__name__)


class RAGResponse:
    """
    RAG response with generated text and metadata
    """

    def __init__(
        self,
        query: str,
        response: str,
        sources: List[Dict[str, Any]],
        retrieved_chunks: List[RetrievedChunk],
        retrieval_time: float,
        generation_time: float,
        total_time: float,
        tokens_used: int = 0,
    ):
        self.query = query
        self.response = response
        self.sources = sources
        self.retrieved_chunks = retrieved_chunks
        self.retrieval_time = retrieval_time
        self.generation_time = generation_time
        self.total_time = total_time
        self.tokens_used = tokens_used

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "query": self.query,
            "response": self.response,
            "sources": self.sources,
            "retrieved_chunks": [chunk.to_dict() for chunk in self.retrieved_chunks],
            "retrieval_time": self.retrieval_time,
            "generation_time": self.generation_time,
            "total_time": self.total_time,
            "tokens_used": self.tokens_used,
        }


class RAGService:
    """
    End-to-end RAG service for Vietnamese legal Q&A
    """

    def __init__(
        self,
        retriever: HybridRetriever = None,
        llm_service: OllamaService = None,
        max_context_tokens: int = None,
    ):
        self.retriever = retriever or get_retriever()
        self.llm_service = llm_service or get_ollama_service()
        self.max_context_tokens = max_context_tokens or settings.MAX_CONTEXT_TOKENS

    async def query(
        self,
        query: str,
        conversation_history: List[Dict[str, str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> RAGResponse:
        """
        Process query using RAG pipeline (non-streaming)

        Args:
            query: User query
            conversation_history: Optional conversation history
            filters: Optional filters for retrieval
            temperature: LLM temperature
            max_tokens: Maximum tokens to generate

        Returns:
            RAGResponse with answer and metadata
        """
        start_time = time.time()

        try:
            # Step 1: Retrieval
            logger.info(f"Processing query: {query[:100]}...")
            retrieval_start = time.time()

            retrieved_chunks = await self.retriever.retrieve(query=query, filters=filters)

            retrieval_time = time.time() - retrieval_start
            logger.info(f"Retrieved {len(retrieved_chunks)} chunks in {retrieval_time:.2f}s")

            if not retrieved_chunks:
                return RAGResponse(
                    query=query,
                    response="Tôi không tìm thấy thông tin liên quan trong cơ sở dữ liệu văn bản pháp luật.",
                    sources=[],
                    retrieved_chunks=[],
                    retrieval_time=retrieval_time,
                    generation_time=0.0,
                    total_time=time.time() - start_time,
                    tokens_used=0,
                )

            # Step 2: Build prompt
            chunks_dicts = [chunk.to_dict() for chunk in retrieved_chunks]
            prompt = build_rag_prompt(
                query=query,
                retrieved_chunks=chunks_dicts,
                conversation_history=conversation_history,
            )

            # Step 3: Generate response
            logger.info("Generating response...")
            generation_start = time.time()

            response = await self.llm_service.generate(
                prompt=prompt,
                system=LEGAL_SYSTEM_PROMPT,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            generation_time = time.time() - generation_start
            logger.info(f"Generated response in {generation_time:.2f}s")

            # Step 4: Extract sources
            sources = self._extract_sources(retrieved_chunks)

            # Step 5: Create response object
            total_time = time.time() - start_time
            rag_response = RAGResponse(
                query=query,
                response=response.strip(),
                sources=sources,
                retrieved_chunks=retrieved_chunks,
                retrieval_time=retrieval_time,
                generation_time=generation_time,
                total_time=total_time,
                tokens_used=self._estimate_tokens(prompt + response),
            )

            logger.info(f"RAG query completed in {total_time:.2f}s")
            return rag_response

        except Exception as e:
            logger.error(f"RAG query error: {e}")
            raise

    async def query_stream(
        self,
        query: str,
        conversation_history: List[Dict[str, str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process query using RAG pipeline with streaming

        Args:
            query: User query
            conversation_history: Optional conversation history
            filters: Optional filters for retrieval
            temperature: LLM temperature
            max_tokens: Maximum tokens to generate

        Yields:
            Response chunks with metadata
        """
        start_time = time.time()

        try:
            # Step 1: Retrieval
            logger.info(f"Processing query (streaming): {query[:100]}...")
            retrieval_start = time.time()

            retrieved_chunks = await self.retriever.retrieve(query=query, filters=filters)

            retrieval_time = time.time() - retrieval_start
            logger.info(f"Retrieved {len(retrieved_chunks)} chunks in {retrieval_time:.2f}s")

            # Yield retrieval metadata first
            sources = self._extract_sources(retrieved_chunks)
            yield {
                "type": "metadata",
                "sources": sources,
                "retrieved_count": len(retrieved_chunks),
                "retrieval_time": retrieval_time,
            }

            if not retrieved_chunks:
                yield {
                    "type": "text",
                    "content": "Tôi không tìm thấy thông tin liên quan trong cơ sở dữ liệu văn bản pháp luật.",
                }
                yield {"type": "done", "total_time": time.time() - start_time}
                return

            # Step 2: Build prompt
            chunks_dicts = [chunk.to_dict() for chunk in retrieved_chunks]
            prompt = build_rag_prompt(
                query=query,
                retrieved_chunks=chunks_dicts,
                conversation_history=conversation_history,
            )

            # Step 3: Stream generation
            logger.info("Streaming response...")
            generation_start = time.time()

            full_response = ""
            async for chunk in self.llm_service.generate_stream(
                prompt=prompt,
                system=LEGAL_SYSTEM_PROMPT,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                full_response += chunk
                yield {"type": "text", "content": chunk}

            generation_time = time.time() - generation_start
            logger.info(f"Streamed response in {generation_time:.2f}s")

            # Step 4: Yield final metadata
            total_time = time.time() - start_time
            yield {
                "type": "done",
                "generation_time": generation_time,
                "total_time": total_time,
                "tokens_used": self._estimate_tokens(prompt + full_response),
            }

            logger.info(f"RAG query (streaming) completed in {total_time:.2f}s")

        except Exception as e:
            logger.error(f"RAG streaming error: {e}")
            yield {"type": "error", "message": f"Đã xảy ra lỗi: {str(e)}"}

    async def query_with_chat_history(
        self,
        query: str,
        conversation_history: List[Dict[str, str]],
        filters: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ):
        """
        Process query with conversation history

        Args:
            query: User query
            conversation_history: Conversation messages
            filters: Optional filters
            temperature: LLM temperature
            max_tokens: Maximum tokens
            stream: Whether to stream response

        Returns:
            RAGResponse or AsyncGenerator
        """
        if stream:
            return self.query_stream(
                query=query,
                conversation_history=conversation_history,
                filters=filters,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            return await self.query(
                query=query,
                conversation_history=conversation_history,
                filters=filters,
                temperature=temperature,
                max_tokens=max_tokens,
            )

    def _extract_sources(self, chunks: List[RetrievedChunk]) -> List[Dict[str, Any]]:
        """
        Extract unique sources from retrieved chunks

        Args:
            chunks: Retrieved chunks

        Returns:
            List of source metadata
        """
        sources = []
        seen_docs = set()

        for chunk in chunks:
            doc_id = chunk.document_id
            if doc_id not in seen_docs:
                seen_docs.add(doc_id)

                metadata = chunk.metadata
                source = {
                    "document_id": doc_id,
                    "document_title": metadata.get("document_title", "Unknown"),
                    "section_title": metadata.get("section_title"),
                    "article_number": metadata.get("article_number"),
                    "page_number": metadata.get("page_number"),
                    "relevance_score": chunk.final_score,
                }

                sources.append(source)

        # Sort by relevance
        sources.sort(key=lambda x: x["relevance_score"], reverse=True)

        return sources[:10]  # Top 10 sources

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count (rough approximation)

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        # Rough estimate: ~0.75 tokens per word for Vietnamese
        words = len(text.split())
        return int(words * 0.75)

    async def check_health(self) -> Dict[str, Any]:
        """
        Check health of RAG components

        Returns:
            Health status
        """
        try:
            # Check LLM
            llm_healthy = await self.llm_service.check_health()

            # Check retriever (basic check)
            retriever_healthy = True
            try:
                # Try a simple retrieval
                await self.retriever.retrieve("test", top_k=1)
            except Exception as e:
                logger.error(f"Retriever health check failed: {e}")
                retriever_healthy = False

            return {
                "healthy": llm_healthy and retriever_healthy,
                "llm_healthy": llm_healthy,
                "retriever_healthy": retriever_healthy,
                "model": self.llm_service.model,
            }

        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {"healthy": False, "error": str(e)}


# Global singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """
    Get global RAG service instance

    Returns:
        RAGService instance
    """
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
