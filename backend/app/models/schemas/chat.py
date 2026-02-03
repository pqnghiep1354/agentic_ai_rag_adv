"""
Pydantic schemas for chat and conversations
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Message schemas
class MessageBase(BaseModel):
    """Base message schema"""

    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")


class MessageCreate(MessageBase):
    """Schema for creating a message"""

    conversation_id: Optional[int] = Field(None, description="Conversation ID")


class MessageResponse(MessageBase):
    """Schema for message response"""

    id: int
    conversation_id: int
    sources: Optional[List[Dict[str, Any]]] = None
    retrieved_chunks: Optional[List[Dict[str, Any]]] = None
    retrieval_score: Optional[float] = None
    processing_time: Optional[float] = None
    tokens_used: Optional[int] = None
    feedback_rating: Optional[int] = None
    feedback_comment: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageFeedback(BaseModel):
    """Schema for message feedback"""

    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = Field(None, description="Feedback comment")


# Conversation schemas
class ConversationBase(BaseModel):
    """Base conversation schema"""

    title: str = Field(..., max_length=255, description="Conversation title")


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation"""

    pass


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation"""

    title: Optional[str] = Field(None, max_length=255, description="New title")
    is_archived: Optional[bool] = Field(None, description="Archive status")


class ConversationResponse(ConversationBase):
    """Schema for conversation response"""

    id: int
    user_id: int
    is_archived: bool
    message_count: int
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None
    messages: Optional[List[MessageResponse]] = None

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    """Schema for conversation list response"""

    conversations: List[ConversationResponse]
    total: int
    skip: int
    limit: int


# Chat request/response schemas
class ChatRequest(BaseModel):
    """Schema for chat request"""

    message: str = Field(..., min_length=1, description="User message")
    conversation_id: Optional[int] = Field(None, description="Existing conversation ID")
    stream: bool = Field(default=False, description="Enable streaming")
    temperature: float = Field(
        default=0.7, ge=0.0, le=1.0, description="LLM temperature"
    )
    max_tokens: int = Field(
        default=2048, ge=100, le=4096, description="Max tokens to generate"
    )


class ChatResponse(BaseModel):
    """Schema for chat response"""

    message: MessageResponse
    conversation_id: int
    sources: Optional[List[Dict[str, Any]]] = None


# Source schema
class Source(BaseModel):
    """Schema for retrieved source"""

    document_id: int
    document_title: str
    section_title: Optional[str] = None
    article_number: Optional[str] = None
    page_number: Optional[int] = None
    relevance_score: float


# WebSocket message types
class WSMessageType:
    """WebSocket message types"""

    METADATA = "metadata"
    TEXT = "text"
    DONE = "done"
    ERROR = "error"


class WSMessage(BaseModel):
    """WebSocket message schema"""

    type: str
    content: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
    retrieved_count: Optional[int] = None
    retrieval_time: Optional[float] = None
    generation_time: Optional[float] = None
    total_time: Optional[float] = None
    tokens_used: Optional[int] = None
    message: Optional[str] = None
    conversation_id: Optional[int] = None
