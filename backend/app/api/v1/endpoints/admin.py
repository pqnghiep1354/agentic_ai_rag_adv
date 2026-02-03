"""
Admin endpoints for dashboard, analytics, and monitoring
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, distinct, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.dependencies import get_current_user, get_db
from app.models.domain.conversation import Conversation, Message
from app.models.domain.document import Document, DocumentStatus
from app.models.domain.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to ensure user is an admin

    Args:
        current_user: Current authenticated user

    Returns:
        User data if admin

    Raises:
        HTTPException: If user is not an admin
    """
    # Check if user has admin role/is_superuser
    # In real implementation, check user.is_superuser from database
    if not current_user.get("is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


@router.get("/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get comprehensive dashboard statistics

    Returns:
        Dashboard data with overview stats, trends, and recent activity
    """
    now = datetime.utcnow()

    # Time ranges for activity tracking
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)

    # Total counts
    total_users = await db.scalar(select(func.count(User.id)))
    total_documents = await db.scalar(select(func.count(Document.id)))
    total_conversations = await db.scalar(select(func.count(Conversation.id)))
    total_messages = await db.scalar(select(func.count(Message.id)))

    # Active users
    active_users_24h = await db.scalar(
        select(func.count(distinct(Conversation.user_id))).where(
            Conversation.last_message_at >= last_24h
        )
    )
    active_users_7d = await db.scalar(
        select(func.count(distinct(Conversation.user_id))).where(
            Conversation.last_message_at >= last_7d
        )
    )
    active_users_30d = await db.scalar(
        select(func.count(distinct(Conversation.user_id))).where(
            Conversation.last_message_at >= last_30d
        )
    )

    # Document status breakdown
    doc_status_query = select(
        Document.status, func.count(Document.id).label("count")
    ).group_by(Document.status)
    doc_status_result = await db.execute(doc_status_query)
    doc_status = {status: count for status, count in doc_status_result.all()}

    # Query metrics (last 7 days)
    query_metrics_query = select(
        func.count(Message.id).label("total_queries"),
        func.avg(Message.processing_time).label("avg_processing_time"),
        func.sum(Message.tokens_used).label("total_tokens"),
        func.avg(Message.retrieval_score).label("avg_retrieval_score"),
        func.avg(Message.feedback_rating).label("avg_feedback_rating"),
    ).where(and_(Message.role == "assistant", Message.created_at >= last_7d))
    query_metrics = (await db.execute(query_metrics_query)).first()

    # Recent activity (last 10 messages)
    recent_activity_query = (
        select(
            Message.id,
            Message.content,
            Message.processing_time,
            Message.tokens_used,
            Message.created_at,
            User.username,
            Conversation.title,
        )
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(User, Conversation.user_id == User.id)
        .where(Message.role == "user")
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    recent_activity = await db.execute(recent_activity_query)
    recent_messages = [
        {
            "id": msg.id,
            "query": (
                msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            ),
            "user": msg.username,
            "conversation": msg.title,
            "processing_time": msg.processing_time,
            "tokens_used": msg.tokens_used,
            "timestamp": msg.created_at.isoformat(),
        }
        for msg in recent_activity.all()
    ]

    # Storage statistics
    total_storage = await db.scalar(select(func.sum(Document.file_size))) or 0
    avg_doc_size = await db.scalar(select(func.avg(Document.file_size))) or 0

    return {
        "overview": {
            "total_users": total_users or 0,
            "total_documents": total_documents or 0,
            "total_conversations": total_conversations or 0,
            "total_messages": total_messages or 0,
            "total_storage_bytes": total_storage,
            "avg_document_size_bytes": avg_doc_size,
        },
        "active_users": {
            "last_24h": active_users_24h or 0,
            "last_7d": active_users_7d or 0,
            "last_30d": active_users_30d or 0,
        },
        "documents": {
            "by_status": {
                "pending": doc_status.get(DocumentStatus.PENDING, 0),
                "processing": doc_status.get(DocumentStatus.PROCESSING, 0),
                "completed": doc_status.get(DocumentStatus.COMPLETED, 0),
                "failed": doc_status.get(DocumentStatus.FAILED, 0),
            }
        },
        "query_metrics": {
            "total_queries_7d": query_metrics.total_queries or 0,
            "avg_processing_time": float(query_metrics.avg_processing_time or 0),
            "total_tokens_7d": query_metrics.total_tokens or 0,
            "avg_retrieval_score": float(query_metrics.avg_retrieval_score or 0),
            "avg_feedback_rating": (
                float(query_metrics.avg_feedback_rating or 0)
                if query_metrics.avg_feedback_rating
                else None
            ),
        },
        "recent_activity": recent_messages,
    }


@router.get("/analytics/documents")
async def get_document_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Get detailed document analytics

    Args:
        days: Number of days to include in analysis

    Returns:
        Document analytics including upload trends, processing stats
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Upload trends by day
    upload_trends_query = (
        select(
            func.date(Document.created_at).label("date"),
            func.count(Document.id).label("count"),
        )
        .where(Document.created_at >= cutoff_date)
        .group_by(func.date(Document.created_at))
        .order_by(func.date(Document.created_at))
    )
    upload_trends = await db.execute(upload_trends_query)
    upload_by_day = [
        {"date": str(row.date), "count": row.count} for row in upload_trends.all()
    ]

    # Processing performance
    processing_stats_query = select(
        func.count(Document.id).label("total"),
        func.avg(
            func.extract("epoch", Document.processed_at - Document.created_at)
        ).label("avg_processing_seconds"),
        func.sum(Document.chunk_count).label("total_chunks"),
        func.avg(Document.chunk_count).label("avg_chunks_per_doc"),
    ).where(
        and_(
            Document.status == DocumentStatus.COMPLETED,
            Document.created_at >= cutoff_date,
        )
    )
    processing_stats = (await db.execute(processing_stats_query)).first()

    # File type distribution
    file_type_query = (
        select(
            Document.file_type,
            func.count(Document.id).label("count"),
            func.sum(Document.file_size).label("total_size"),
        )
        .where(Document.created_at >= cutoff_date)
        .group_by(Document.file_type)
    )
    file_types = await db.execute(file_type_query)
    file_type_distribution = [
        {
            "file_type": row.file_type,
            "count": row.count,
            "total_size_bytes": row.total_size or 0,
        }
        for row in file_types.all()
    ]

    # Top uploaders
    top_uploaders_query = (
        select(
            User.username,
            func.count(Document.id).label("upload_count"),
            func.sum(Document.file_size).label("total_size"),
        )
        .join(User, Document.owner_id == User.id)
        .where(Document.created_at >= cutoff_date)
        .group_by(User.username)
        .order_by(func.count(Document.id).desc())
        .limit(10)
    )
    top_uploaders = await db.execute(top_uploaders_query)
    top_users = [
        {
            "username": row.username,
            "upload_count": row.upload_count,
            "total_size_bytes": row.total_size or 0,
        }
        for row in top_uploaders.all()
    ]

    return {
        "time_range_days": days,
        "upload_trends": upload_by_day,
        "processing_performance": {
            "total_processed": processing_stats.total or 0,
            "avg_processing_seconds": float(
                processing_stats.avg_processing_seconds or 0
            ),
            "total_chunks": processing_stats.total_chunks or 0,
            "avg_chunks_per_document": float(processing_stats.avg_chunks_per_doc or 0),
        },
        "file_type_distribution": file_type_distribution,
        "top_uploaders": top_users,
    }


@router.get("/analytics/queries")
async def get_query_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Get detailed query analytics and performance metrics

    Args:
        days: Number of days to include in analysis

    Returns:
        Query analytics including performance, usage patterns, feedback
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Query volume by day
    query_volume_query = (
        select(
            func.date(Message.created_at).label("date"),
            func.count(Message.id).label("count"),
        )
        .where(and_(Message.role == "assistant", Message.created_at >= cutoff_date))
        .group_by(func.date(Message.created_at))
        .order_by(func.date(Message.created_at))
    )
    query_volume = await db.execute(query_volume_query)
    queries_by_day = [
        {"date": str(row.date), "count": row.count} for row in query_volume.all()
    ]

    # Performance metrics (percentiles)
    performance_query = select(
        func.count(Message.id).label("total"),
        func.min(Message.processing_time).label("min_time"),
        func.max(Message.processing_time).label("max_time"),
        func.avg(Message.processing_time).label("avg_time"),
        func.percentile_cont(0.50)
        .within_group(Message.processing_time)
        .label("p50_time"),
        func.percentile_cont(0.95)
        .within_group(Message.processing_time)
        .label("p95_time"),
        func.percentile_cont(0.99)
        .within_group(Message.processing_time)
        .label("p99_time"),
    ).where(
        and_(
            Message.role == "assistant",
            Message.created_at >= cutoff_date,
            Message.processing_time.isnot(None),
        )
    )
    performance = (await db.execute(performance_query)).first()

    # Token usage
    token_stats_query = select(
        func.sum(Message.tokens_used).label("total_tokens"),
        func.avg(Message.tokens_used).label("avg_tokens"),
        func.max(Message.tokens_used).label("max_tokens"),
    ).where(
        and_(
            Message.role == "assistant",
            Message.created_at >= cutoff_date,
            Message.tokens_used.isnot(None),
        )
    )
    token_stats = (await db.execute(token_stats_query)).first()

    # Feedback distribution
    feedback_query = (
        select(Message.feedback_rating, func.count(Message.id).label("count"))
        .where(
            and_(Message.created_at >= cutoff_date, Message.feedback_rating.isnot(None))
        )
        .group_by(Message.feedback_rating)
    )
    feedback = await db.execute(feedback_query)
    feedback_distribution = {
        int(row.feedback_rating): row.count for row in feedback.all()
    }

    # Most active users
    active_users_query = (
        select(
            User.username,
            func.count(distinct(Conversation.id)).label("conversation_count"),
            func.count(Message.id).label("message_count"),
            func.avg(Message.processing_time).label("avg_processing_time"),
        )
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(User, Conversation.user_id == User.id)
        .where(and_(Message.role == "user", Message.created_at >= cutoff_date))
        .group_by(User.username)
        .order_by(func.count(Message.id).desc())
        .limit(10)
    )
    active_users = await db.execute(active_users_query)
    top_users = [
        {
            "username": row.username,
            "conversations": row.conversation_count,
            "messages": row.message_count,
            "avg_processing_time": float(row.avg_processing_time or 0),
        }
        for row in active_users.all()
    ]

    return {
        "time_range_days": days,
        "query_volume": queries_by_day,
        "performance": {
            "total_queries": performance.total or 0,
            "min_time": float(performance.min_time or 0),
            "max_time": float(performance.max_time or 0),
            "avg_time": float(performance.avg_time or 0),
            "p50_time": float(performance.p50_time or 0),
            "p95_time": float(performance.p95_time or 0),
            "p99_time": float(performance.p99_time or 0),
        },
        "token_usage": {
            "total_tokens": token_stats.total_tokens or 0,
            "avg_tokens": float(token_stats.avg_tokens or 0),
            "max_tokens": token_stats.max_tokens or 0,
        },
        "feedback": {
            "distribution": feedback_distribution,
            "total_responses": sum(feedback_distribution.values()),
        },
        "top_users": top_users,
    }


@router.get("/users")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by username or email"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> Dict[str, Any]:
    """
    List all users with pagination and search

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        search: Optional search term

    Returns:
        List of users with metadata
    """
    # Build query
    query = select(User)

    if search:
        search_filter = or_(
            User.username.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
            User.full_name.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
    result = await db.execute(query)
    users = result.scalars().all()

    return {
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "created_at": user.created_at.isoformat(),
            }
            for user in users
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/logs/queries")
async def get_query_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    min_processing_time: Optional[float] = Query(
        None, description="Min processing time (seconds)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Get query logs for monitoring and debugging

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        user_id: Optional user ID filter
        min_processing_time: Optional filter for slow queries

    Returns:
        List of query logs
    """
    # Build query
    query = (
        select(
            Message.id,
            Message.content,
            Message.processing_time,
            Message.tokens_used,
            Message.retrieval_score,
            Message.feedback_rating,
            Message.created_at,
            User.username,
            Conversation.id.label("conversation_id"),
            Conversation.title.label("conversation_title"),
        )
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(User, Conversation.user_id == User.id)
        .where(Message.role == "user")
    )

    # Apply filters
    if user_id:
        query = query.where(User.id == user_id)
    if min_processing_time:
        query = query.where(Message.processing_time >= min_processing_time)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results
    query = query.order_by(Message.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.all()

    return {
        "logs": [
            {
                "message_id": log.id,
                "query": log.content,
                "user": log.username,
                "conversation_id": log.conversation_id,
                "conversation_title": log.conversation_title,
                "processing_time": log.processing_time,
                "tokens_used": log.tokens_used,
                "retrieval_score": log.retrieval_score,
                "feedback_rating": log.feedback_rating,
                "timestamp": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }
