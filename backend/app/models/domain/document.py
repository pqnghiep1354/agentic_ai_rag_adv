"""
Document domain model
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.domain.user import User


class DocumentStatus(str, Enum):
    """Document processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    """Document model for uploaded legal documents"""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, docx, etc.
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # in bytes

    # Content metadata
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    issuing_authority: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    issue_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    document_number: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Processing status
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False
    )
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Statistics
    chunk_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    entity_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Ownership
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title={self.title}, status={self.status})>"
