"""
Hierarchical chunking utilities for legal documents.
Preserves document structure and legal boundaries (clauses, articles, sections).
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re

from app.utils.document_parser import DocumentElement

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""

    text: str
    chunk_id: str
    document_id: int
    page_number: Optional[int]
    hierarchy_level: int
    hierarchy_path: str  # e.g., "Chapter 1 > Section 2 > Article 5"
    parent_chunk_id: Optional[str]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "page_number": self.page_number,
            "hierarchy_level": self.hierarchy_level,
            "hierarchy_path": self.hierarchy_path,
            "parent_chunk_id": self.parent_chunk_id,
            "metadata": self.metadata,
        }


class HierarchicalChunker:
    """
    Hierarchical chunker that preserves legal document structure.

    Approach:
    - Respects document hierarchy (Chapter > Section > Article > Clause)
    - Keeps related content together
    - Adds overlap between chunks for context
    - Maintains parent-child relationships
    """

    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 128,
        min_chunk_size: int = 100,
    ):
        """
        Initialize chunker.

        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks in characters
            min_chunk_size: Minimum chunk size to avoid tiny chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.hierarchy_stack: List[DocumentElement] = []

    def chunk_document(
        self,
        elements: List[DocumentElement],
        document_id: int,
    ) -> List[Chunk]:
        """
        Chunk a parsed document while preserving hierarchy.

        Args:
            elements: Parsed document elements
            document_id: Database ID of the document

        Returns:
            List of chunks with hierarchy metadata
        """
        logger.info(f"Chunking document {document_id} with {len(elements)} elements")

        chunks: List[Chunk] = []
        self.hierarchy_stack = []

        current_section: List[DocumentElement] = []
        chunk_counter = 0

        for element in elements:
            # Update hierarchy stack
            self._update_hierarchy_stack(element)

            # Check if this is a major boundary (Chapter/Section)
            if element.hierarchy_level <= 2:
                # Flush current section first
                if current_section:
                    section_chunks = self._create_chunks_from_section(
                        current_section,
                        document_id,
                        chunk_counter,
                    )
                    chunks.extend(section_chunks)
                    chunk_counter += len(section_chunks)
                    current_section = []

                # Start new section with this element
                current_section = [element]
            else:
                current_section.append(element)

            # Check if section is getting too large
            section_text = " ".join(e.text for e in current_section)
            if len(section_text) > self.chunk_size * 2:
                section_chunks = self._create_chunks_from_section(
                    current_section,
                    document_id,
                    chunk_counter,
                )
                chunks.extend(section_chunks)
                chunk_counter += len(section_chunks)
                current_section = []

        # Flush remaining section
        if current_section:
            section_chunks = self._create_chunks_from_section(
                current_section,
                document_id,
                chunk_counter,
            )
            chunks.extend(section_chunks)

        logger.info(f"Created {len(chunks)} chunks from document {document_id}")
        return chunks

    def _update_hierarchy_stack(self, element: DocumentElement) -> None:
        """Update the hierarchy stack based on current element."""
        # Pop elements from stack that are at same or lower level
        while self.hierarchy_stack and self.hierarchy_stack[-1].hierarchy_level >= element.hierarchy_level:
            self.hierarchy_stack.pop()

        # Add current element if it's a title/heading
        if element.element_type.startswith("title"):
            self.hierarchy_stack.append(element)

    def _get_hierarchy_path(self) -> str:
        """Get current hierarchy path as string."""
        if not self.hierarchy_stack:
            return ""

        path_parts = []
        for elem in self.hierarchy_stack:
            # Extract short identifier
            text = elem.text.strip()
            # Limit to first 50 chars
            if len(text) > 50:
                text = text[:50] + "..."
            path_parts.append(text)

        return " > ".join(path_parts)

    def _create_chunks_from_section(
        self,
        section_elements: List[DocumentElement],
        document_id: int,
        start_index: int,
    ) -> List[Chunk]:
        """Create chunks from a section of elements."""
        if not section_elements:
            return []

        # Combine section text
        section_text = "\n\n".join(e.text for e in section_elements)

        # Get metadata from first element
        first_elem = section_elements[0]
        page_number = first_elem.page_number
        hierarchy_level = max(e.hierarchy_level for e in section_elements)

        # If section fits in one chunk, return as-is
        if len(section_text) <= self.chunk_size:
            chunk = Chunk(
                text=section_text,
                chunk_id=f"{document_id}_chunk_{start_index}",
                document_id=document_id,
                page_number=page_number,
                hierarchy_level=hierarchy_level,
                hierarchy_path=self._get_hierarchy_path(),
                parent_chunk_id=None,
                metadata={
                    "element_count": len(section_elements),
                    "element_types": [e.element_type for e in section_elements],
                },
            )
            return [chunk]

        # Split into multiple chunks with overlap
        chunks = []
        words = section_text.split()
        current_chunk_words = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1  # +1 for space

            if current_length + word_length > self.chunk_size and len(current_chunk_words) > 0:
                # Create chunk
                chunk_text = " ".join(current_chunk_words)

                if len(chunk_text) >= self.min_chunk_size:
                    chunk = Chunk(
                        text=chunk_text,
                        chunk_id=f"{document_id}_chunk_{start_index + len(chunks)}",
                        document_id=document_id,
                        page_number=page_number,
                        hierarchy_level=hierarchy_level,
                        hierarchy_path=self._get_hierarchy_path(),
                        parent_chunk_id=None,
                        metadata={
                            "is_continuation": len(chunks) > 0,
                        },
                    )
                    chunks.append(chunk)

                # Calculate overlap words
                overlap_char_count = 0
                overlap_words = []
                for w in reversed(current_chunk_words):
                    if overlap_char_count + len(w) > self.chunk_overlap:
                        break
                    overlap_words.insert(0, w)
                    overlap_char_count += len(w) + 1

                # Start new chunk with overlap
                current_chunk_words = overlap_words + [word]
                current_length = sum(len(w) + 1 for w in current_chunk_words)
            else:
                current_chunk_words.append(word)
                current_length += word_length

        # Add final chunk
        if current_chunk_words:
            chunk_text = " ".join(current_chunk_words)
            if len(chunk_text) >= self.min_chunk_size:
                chunk = Chunk(
                    text=chunk_text,
                    chunk_id=f"{document_id}_chunk_{start_index + len(chunks)}",
                    document_id=document_id,
                    page_number=page_number,
                    hierarchy_level=hierarchy_level,
                    hierarchy_path=self._get_hierarchy_path(),
                    parent_chunk_id=None,
                    metadata={
                        "is_continuation": len(chunks) > 0,
                        "is_final": True,
                    },
                )
                chunks.append(chunk)

        return chunks


def extract_legal_references(text: str) -> List[str]:
    """
    Extract legal references from Vietnamese text.

    Examples:
    - "Điều 5 Luật Bảo vệ môi trường"
    - "Khoản 2 Điều 10"
    - "Nghị định 08/2022/NĐ-CP"

    Args:
        text: Vietnamese legal text

    Returns:
        List of extracted references
    """
    references = []

    # Pattern for "Điều X" (Article X)
    article_pattern = r"Điều\s+\d+"
    references.extend(re.findall(article_pattern, text, re.IGNORECASE))

    # Pattern for "Khoản X Điều Y" (Clause X Article Y)
    clause_article_pattern = r"Khoản\s+\d+\s+Điều\s+\d+"
    references.extend(re.findall(clause_article_pattern, text, re.IGNORECASE))

    # Pattern for "Nghị định XX/YYYY/NĐ-CP"
    decree_pattern = r"Nghị định\s+\d+/\d+/[A-Z\-]+"
    references.extend(re.findall(decree_pattern, text, re.IGNORECASE))

    # Pattern for "Luật ABC năm YYYY" (Law ABC year YYYY)
    law_pattern = r"Luật\s+[^\n]+năm\s+\d{4}"
    references.extend(re.findall(law_pattern, text, re.IGNORECASE))

    # Pattern for "Thông tư XX/YYYY/TT-ABC"
    circular_pattern = r"Thông tư\s+\d+/\d+/[A-Z\-]+"
    references.extend(re.findall(circular_pattern, text, re.IGNORECASE))

    return list(set(references))  # Remove duplicates


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract legal entities from Vietnamese text.

    Entity types:
    - Laws (Luật)
    - Decrees (Nghị định)
    - Circulars (Thông tư)
    - Decisions (Quyết định)
    - Articles (Điều)
    - Clauses (Khoản)

    Args:
        text: Vietnamese legal text

    Returns:
        Dictionary mapping entity types to lists of entities
    """
    entities = {
        "laws": [],
        "decrees": [],
        "circulars": [],
        "decisions": [],
        "articles": [],
        "clauses": [],
    }

    # Extract laws
    law_pattern = r"Luật\s+[^\n,;\.]+(?:năm\s+\d{4})?"
    entities["laws"] = re.findall(law_pattern, text, re.IGNORECASE)

    # Extract decrees
    decree_pattern = r"Nghị định\s+(?:\d+/\d+/[A-Z\-]+|số\s+\d+)"
    entities["decrees"] = re.findall(decree_pattern, text, re.IGNORECASE)

    # Extract circulars
    circular_pattern = r"Thông tư\s+(?:\d+/\d+/[A-Z\-]+|số\s+\d+)"
    entities["circulars"] = re.findall(circular_pattern, text, re.IGNORECASE)

    # Extract decisions
    decision_pattern = r"Quyết định\s+(?:\d+/\d+/[A-Z\-]+|số\s+\d+)"
    entities["decisions"] = re.findall(decision_pattern, text, re.IGNORECASE)

    # Extract articles
    article_pattern = r"Điều\s+\d+"
    entities["articles"] = re.findall(article_pattern, text, re.IGNORECASE)

    # Extract clauses
    clause_pattern = r"Khoản\s+\d+"
    entities["clauses"] = re.findall(clause_pattern, text, re.IGNORECASE)

    # Remove duplicates and clean
    for key in entities:
        entities[key] = list(set(e.strip() for e in entities[key]))

    return entities
