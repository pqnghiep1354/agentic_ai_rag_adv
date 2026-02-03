"""
Chat API endpoints for conversations and Q&A
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.dependencies import get_current_user
from ....models.domain.conversation import Conversation, Message
from ....models.domain.user import User
from ....models.schemas.chat import (ChatRequest, ChatResponse,
                                     ConversationCreate,
                                     ConversationListResponse,
                                     ConversationResponse, ConversationUpdate,
                                     MessageFeedback, MessageResponse)
from ....services.rag_service import get_rag_service

router = APIRouter()
rag_service = get_rag_service()


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Chat endpoint - ask questions and get answers

    Creates a new conversation if conversation_id is not provided
    """
    try:
        # Get or create conversation
        if request.conversation_id:
            # Get existing conversation
            result = await db.execute(
                select(Conversation).where(
                    Conversation.id == request.conversation_id,
                    Conversation.user_id == current_user.id,
                )
            )
            conversation = result.scalar_one_or_none()

            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found",
                )
        else:
            # Create new conversation
            conversation = Conversation(
                title=request.message[:100],  # Use first 100 chars as title
                user_id=current_user.id,
            )
            db.add(conversation)
            await db.flush()

        # Get conversation history
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at)
            .limit(10)  # Last 10 messages
        )
        history_messages = result.scalars().all()

        # Build conversation history for context
        conversation_history = [
            {"role": msg.role, "content": msg.content} for msg in history_messages
        ]

        # Create user message
        user_message = Message(
            conversation_id=conversation.id, role="user", content=request.message
        )
        db.add(user_message)
        await db.flush()

        # Query RAG service
        rag_response = await rag_service.query(
            query=request.message,
            conversation_history=conversation_history,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        # Create assistant message
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=rag_response.response,
            sources=rag_response.sources,
            retrieved_chunks=[
                chunk.to_dict() for chunk in rag_response.retrieved_chunks
            ],
            retrieval_score=(
                sum(chunk.final_score for chunk in rag_response.retrieved_chunks)
                / len(rag_response.retrieved_chunks)
                if rag_response.retrieved_chunks
                else 0.0
            ),
            processing_time=rag_response.total_time,
            tokens_used=rag_response.tokens_used,
        )
        db.add(assistant_message)

        # Update conversation
        conversation.last_message_at = datetime.utcnow()
        conversation.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(assistant_message)

        return ChatResponse(
            message=MessageResponse.model_validate(assistant_message),
            conversation_id=conversation.id,
            sources=rag_response.sources,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat error: {str(e)}",
        )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    include_archived: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List user's conversations
    """
    try:
        # Build query
        query = select(Conversation).where(Conversation.user_id == current_user.id)

        if not include_archived:
            query = query.where(Conversation.is_archived.is_(False))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Get conversations
        query = query.order_by(desc(Conversation.updated_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        conversations = result.scalars().all()

        return ConversationListResponse(
            conversations=[
                ConversationResponse.model_validate(conv) for conv in conversations
            ],
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list conversations: {str(e)}",
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    include_messages: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific conversation with messages
    """
    try:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

        if include_messages:
            # Load messages
            result = await db.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
            conversation.messages = result.scalars().all()

        return ConversationResponse.model_validate(conversation)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation: {str(e)}",
        )


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    conversation: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new conversation
    """
    try:
        new_conversation = Conversation(
            title=conversation.title, user_id=current_user.id
        )
        db.add(new_conversation)
        await db.commit()
        await db.refresh(new_conversation)

        return ConversationResponse.model_validate(new_conversation)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}",
        )


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    update: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a conversation (title, archive status)
    """
    try:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

        # Update fields
        if update.title is not None:
            conversation.title = update.title
        if update.is_archived is not None:
            conversation.is_archived = update.is_archived

        conversation.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(conversation)

        return ConversationResponse.model_validate(conversation)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update conversation: {str(e)}",
        )


@router.delete(
    "/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a conversation and all its messages
    """
    try:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

        await db.delete(conversation)
        await db.commit()

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}",
        )


@router.post("/messages/{message_id}/feedback", response_model=MessageResponse)
async def submit_feedback(
    message_id: int,
    feedback: MessageFeedback,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit feedback for a message
    """
    try:
        # Get message and verify ownership
        result = await db.execute(
            select(Message)
            .join(Conversation)
            .where(Message.id == message_id, Conversation.user_id == current_user.id)
        )
        message = result.scalar_one_or_none()

        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
            )

        # Update feedback
        message.feedback_rating = feedback.rating
        message.feedback_comment = feedback.comment

        await db.commit()
        await db.refresh(message)

        return MessageResponse.model_validate(message)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}",
        )
