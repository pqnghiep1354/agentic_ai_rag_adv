"""
Document parser for Vietnamese legal documents.
Supports PDF and DOCX formats with hierarchical structure extraction.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from docx import Document
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class DocumentElement:
    """
    Represents a hierarchical element in the document
    """
    element_type: str  # title, section, article, paragraph, etc.
    text: str
    level: int  # Hierarchy level (0=root, 1=chapter, 2=section, etc.)
    page_number: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PDFParser:
    """
    Parser for PDF documents using PyMuPDF
    """

    def __init__(self):
        self.legal_patterns = {
            "law": re.compile(r"^(LUẬT|Luật)\s+[A-ZĐ\s]+", re.IGNORECASE),
            "decree": re.compile(r"^(NGHỊ ĐỊNH|Nghị định)\s+\d+\/\d+\/[A-Z\-]+", re.IGNORECASE),
            "circular": re.compile(r"^(THÔNG TƯ|Thông tư)\s+\d+\/\d+\/[A-Z\-]+", re.IGNORECASE),
            "chapter": re.compile(r"^Chương\s+[IVXLCDM\d]+", re.IGNORECASE),
            "section": re.compile(r"^Mục\s+\d+", re.IGNORECASE),
            "article": re.compile(r"^Điều\s+\d+", re.IGNORECASE),
            "clause": re.compile(r"^\d+\.\s+", re.IGNORECASE),
        }

    def parse(self, file_path: str) -> tuple[List[DocumentElement], Dict[str, Any]]:
        """
        Parse PDF document

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (elements list, metadata dict)
        """
        try:
            elements = []
            metadata = {}

            # Use PyMuPDF for basic extraction
            pdf_doc = fitz.open(file_path)
            metadata["page_count"] = pdf_doc.page_count

            for page_num in range(pdf_doc.page_count):
                page = pdf_doc[page_num]
                text = page.get_text()

                # Split into blocks
                blocks = text.split("\n\n")

                for block in blocks:
                    if not block.strip():
                        continue

                    element = self._classify_element(block.strip(), page_num + 1)
                    if element:
                        elements.append(element)

            pdf_doc.close()

            # Extract document title from first elements
            if elements:
                metadata["title"] = elements[0].text[:200]

            logger.info(f"Parsed PDF: {len(elements)} elements, {metadata['page_count']} pages")
            return elements, metadata

        except Exception as e:
            logger.error(f"PDF parsing error: {e}")
            raise

    def _classify_element(self, text: str, page_number: int) -> Optional[DocumentElement]:
        """
        Classify text element by type and level

        Args:
            text: Element text
            page_number: Page number

        Returns:
            DocumentElement or None
        """
        text = text.strip()
        if not text or len(text) < 3:
            return None

        # Check patterns
        if self.legal_patterns["law"].match(text):
            return DocumentElement(
                element_type="title",
                text=text,
                level=0,
                page_number=page_number
            )
        elif self.legal_patterns["decree"].match(text) or self.legal_patterns["circular"].match(text):
            return DocumentElement(
                element_type="title",
                text=text,
                level=1,
                page_number=page_number
            )
        elif self.legal_patterns["chapter"].match(text):
            return DocumentElement(
                element_type="chapter",
                text=text,
                level=2,
                page_number=page_number
            )
        elif self.legal_patterns["section"].match(text):
            return DocumentElement(
                element_type="section",
                text=text,
                level=3,
                page_number=page_number
            )
        elif self.legal_patterns["article"].match(text):
            return DocumentElement(
                element_type="article",
                text=text,
                level=4,
                page_number=page_number
            )
        elif self.legal_patterns["clause"].match(text):
            return DocumentElement(
                element_type="clause",
                text=text,
                level=5,
                page_number=page_number
            )
        else:
            # Default to paragraph
            level = self._infer_title_level(text)
            return DocumentElement(
                element_type="paragraph",
                text=text,
                level=level,
                page_number=page_number
            )

    def _infer_title_level(self, text: str) -> int:
        """
        Infer title level from text characteristics

        Args:
            text: Element text

        Returns:
            Level (1-5)
        """
        text_lower = text.lower().strip()

        # Check for common legal document keywords
        if any(keyword in text_lower for keyword in ["luật", "nghị định", "thông tư", "quyết định"]):
            return 1
        elif text_lower.startswith("chương"):
            return 2
        elif text_lower.startswith("mục"):
            return 3
        elif text_lower.startswith("điều"):
            return 4
        else:
            return 3  # Default level


class DOCXParser:
    """
    Parser for DOCX documents using python-docx
    """

    def __init__(self):
        self.pdf_parser = PDFParser()

    def parse(self, file_path: str) -> tuple[List[DocumentElement], Dict[str, Any]]:
        """
        Parse DOCX document

        Args:
            file_path: Path to DOCX file

        Returns:
            Tuple of (elements list, metadata dict)
        """
        try:
            elements = []
            metadata = {}

            doc = Document(file_path)

            # Extract paragraphs
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue

                # Use same classification as PDF parser
                element = self.pdf_parser._classify_element(text, 0)
                if element:
                    elements.append(element)

            # Extract tables
            for table in doc.tables:
                table_text = self._extract_table_text(table)
                if table_text:
                    elements.append(DocumentElement(
                        element_type="table",
                        text=table_text,
                        level=5,
                        page_number=0
                    ))

            metadata["paragraph_count"] = len(doc.paragraphs)
            metadata["table_count"] = len(doc.tables)

            if elements:
                metadata["title"] = elements[0].text[:200]

            logger.info(f"Parsed DOCX: {len(elements)} elements")
            return elements, metadata

        except Exception as e:
            logger.error(f"DOCX parsing error: {e}")
            raise

    def _extract_table_text(self, table) -> str:
        """Extract text from table"""
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(" | ".join(cells))
        return "\n".join(rows)


def parse_document(file_path: str) -> tuple[List[DocumentElement], Dict[str, Any]]:
    """
    Parse document (PDF or DOCX)

    Args:
        file_path: Path to document file

    Returns:
        Tuple of (elements list, metadata dict)
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        parser = PDFParser()
    elif suffix in [".docx", ".doc"]:
        parser = DOCXParser()
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    return parser.parse(file_path)
