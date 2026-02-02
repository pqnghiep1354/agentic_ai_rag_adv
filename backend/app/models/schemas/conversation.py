"""
Conversation and Message Pydantic schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# Message schemas
class MessageBase(BaseModel):
    """Base message schema"""
    content: str


class MessageCreate(MessageBase):
    """Schema for creating a message"""
    role: str = Field(..., pattern="^(user|assistant|system)$")


class MessageInDB(MessageBase):
    """Schema for message in database"""
    id: int
    conversation_id: int
    role: str
    sources: Optional[dict] = None
    retrieved_chunks: Optional[list] = None
    retrieval_score: Optional[float] = None
    processing_time: Optional[float] = None
    tokens_used: Optional[int] = None
    feedback_rating: Optional[int] = None
    feedback_comment: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Message(MessageInDB):
    """Schema for message response"""
    pass


class MessageFeedback(BaseModel):
    """Schema for message feedback"""
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


# Conversation schemas
class ConversationBase(BaseModel):
    """Base conversation schema"""
    title: str = Field(..., max_length=500)


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation"""
    pass


class ConversationUpdate(BaseModel):
    """Schema for updating conversation"""
    title: Optional[str] = Field(None, max_length=500)
    is_archived: Optional[bool] = None


class ConversationInDB(ConversationBase):
    """Schema for conversation in database"""
    id: int
    user_id: int
    is_archived: bool
    message_count: int
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Conversation(ConversationInDB):
    """Schema for conversation response"""
    messages: Optional[List[Message]] = None


class ConversationList(BaseModel):
    """Schema for paginated conversation list"""
    items: List[Conversation]
    total: int
    page: int
    page_size: int
    total_pages: int


# Chat schemas
class ChatRequest(BaseModel):
    """Schema for chat request"""
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    """Schema for chat response"""
    message: Message
    conversation_id: int
    sources: Optional[List[dict]] = None
