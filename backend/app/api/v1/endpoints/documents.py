"""
Document management endpoints.
Handles upload, listing, deletion, and status tracking of documents.
"""

import logging
import os
import shutil
from typing import Optional
from uuid import uuid4

from fastapi import (APIRouter, BackgroundTasks, Depends, File, HTTPException,
                     UploadFile, status)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.models.domain.document import Document, DocumentStatus
from app.models.domain.user import User
from app.models.schemas.document import (DocumentListResponse,
                                         DocumentResponse, DocumentUpdate)

logger = logging.getLogger(__name__)
router = APIRouter()


# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE  # 50MB from .env


async def validate_file(file: UploadFile) -> None:
    """Validate uploaded file type and size."""
    # Check extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Check file size (read first chunk to verify it's not empty)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty",
        )

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB",
        )


async def save_upload_file(file: UploadFile, destination: str) -> None:
    """Save uploaded file to disk."""
    os.makedirs(os.path.dirname(destination), exist_ok=True)

    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)


@router.post(
    "/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """
    Upload a PDF or DOCX document for processing.

    - **file**: PDF or DOCX file (max 50MB)

    Returns the created document with status PENDING.
    Processing will happen in the background.
    """
    # Validate file
    await validate_file(file)

    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1].lower()
    unique_filename = f"{uuid4()}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, str(current_user.id), unique_filename)

    # Save file to disk
    await save_upload_file(file, file_path)

    # Create database record
    document = Document(
        filename=file.filename,
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        mime_type=file.content_type or "application/octet-stream",
        status=DocumentStatus.PENDING,
        owner_id=current_user.id,
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Trigger background processing
    from app.services.document_processor import get_document_processor

    async def process_document_task(doc_id: int):
        """Background task to process document."""
        from app.core.database import get_session_maker

        async_session = get_session_maker()
        async with async_session() as session:
            processor = get_document_processor()
            try:
                await processor.process_document(doc_id, session)
            except Exception as e:
                logger.error(f"Background processing failed for document {doc_id}: {e}")

    background_tasks.add_task(process_document_task, document.id)

    return DocumentResponse.model_validate(document)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[DocumentStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    """
    List all documents for the current user.

    - **skip**: Number of documents to skip (pagination)
    - **limit**: Maximum number of documents to return
    - **status_filter**: Filter by document status (optional)
    """
    from sqlalchemy import func, select

    # Base query
    query = select(Document).where(Document.owner_id == current_user.id)

    if status_filter:
        query = query.where(Document.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()

    # Get documents with pagination
    query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    documents = result.scalars().all()

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(doc) for doc in documents],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Get a specific document by ID."""
    from sqlalchemy import select

    query = select(Document).where(
        Document.id == document_id,
        Document.owner_id == current_user.id,
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentResponse.model_validate(document)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Update document metadata (e.g., rename)."""
    from sqlalchemy import select

    query = select(Document).where(
        Document.id == document_id,
        Document.owner_id == current_user.id,
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Update fields
    update_data = document_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)

    await db.commit()
    await db.refresh(document)

    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete a document and its associated data.

    This will:
    - Delete the file from disk
    - Delete vectors from Qdrant
    - Delete nodes from Neo4j
    - Delete the database record
    """
    from sqlalchemy import select

    query = select(Document).where(
        Document.id == document_id,
        Document.owner_id == current_user.id,
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Delete file from disk
    if os.path.exists(document.file_path):
        os.remove(document.file_path)

    # TODO: Delete from Qdrant
    # TODO: Delete from Neo4j

    # Delete from database
    await db.delete(document)
    await db.commit()


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    document_id: int,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """
    Reprocess a document (useful if processing failed).

    Sets status back to PENDING and triggers background processing.
    """
    from sqlalchemy import select

    query = select(Document).where(
        Document.id == document_id,
        Document.owner_id == current_user.id,
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Reset status
    document.status = DocumentStatus.PENDING
    document.error_message = None
    document.processing_time = None

    await db.commit()
    await db.refresh(document)

    # Trigger background processing
    from app.services.document_processor import get_document_processor

    async def reprocess_document_task(doc_id: int):
        """Background task to reprocess document."""
        from app.core.database import get_session_maker

        async_session = get_session_maker()
        async with async_session() as session:
            processor = get_document_processor()
            try:
                await processor.reprocess_document(doc_id, session)
            except Exception as e:
                logger.error(
                    f"Background reprocessing failed for document {doc_id}: {e}"
                )

    background_tasks.add_task(reprocess_document_task, document.id)

    return DocumentResponse.model_validate(document)
