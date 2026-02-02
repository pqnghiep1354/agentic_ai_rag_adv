"""
Conversation and Message domain models
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Conversation(Base):
    """Conversation model for chat sessions"""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)

    # User ownership
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Metadata
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, title={self.title}, user_id={self.user_id})>"


class Message(Base):
    """Message model for individual messages in conversations"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False)

    # Message content
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # RAG metadata (for assistant messages)
    sources: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Citation sources
    retrieved_chunks: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # Chunk IDs
    retrieval_score: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Performance metrics
    processing_time: Mapped[Optional[float]] = mapped_column(nullable=True)  # seconds
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # User feedback
    feedback_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    feedback_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"
