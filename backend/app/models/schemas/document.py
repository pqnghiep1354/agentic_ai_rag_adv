"""
Document Pydantic schemas for API validation
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.models.domain.document import DocumentStatus


# Base schemas
class DocumentBase(BaseModel):
    """Base document schema"""
    title: str = Field(..., max_length=500)


class DocumentCreate(DocumentBase):
    """Schema for creating a document (from upload)"""
    pass


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata"""
    title: Optional[str] = Field(None, max_length=500)
    issuing_authority: Optional[str] = Field(None, max_length=500)
    issue_date: Optional[datetime] = None
    document_number: Optional[str] = Field(None, max_length=200)


class DocumentInDB(DocumentBase):
    """Schema for document in database"""
    id: int
    filename: str
    file_path: str
    file_type: str
    file_size: int
    page_count: Optional[int] = None
    issuing_authority: Optional[str] = None
    issue_date: Optional[datetime] = None
    document_number: Optional[str] = None
    status: DocumentStatus
    processing_error: Optional[str] = None
    chunk_count: Optional[int] = None
    entity_count: Optional[int] = None
    owner_id: int
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(DocumentInDB):
    """Schema for document response"""
    pass


class DocumentListResponse(BaseModel):
    """Schema for paginated document list"""
    documents: list[DocumentResponse]
    total: int
    skip: int
    limit: int


class DocumentUploadResponse(BaseModel):
    """Response after document upload"""
    document_id: int
    filename: str
    status: DocumentStatus
    message: str
