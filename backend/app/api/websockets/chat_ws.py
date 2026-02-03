"""
WebSocket endpoint for real-time chat streaming
"""

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.security import decode_token
from ...models.domain.conversation import Conversation, Message
from ...models.domain.user import User
from ...services.rag_service import get_rag_service

logger = logging.getLogger(__name__)
rag_service = get_rag_service()


class ConnectionManager:
    """
    WebSocket connection manager
    """

    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected via WebSocket")

    def disconnect(self, user_id: int):
        """Remove WebSocket connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected from WebSocket")

    async def send_message(self, user_id: int, message: dict):
        """Send message to specific user"""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_json(message)

    async def send_text(self, user_id: int, text: str):
        """Send text message to specific user"""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_text(text)


manager = ConnectionManager()


async def get_current_user_ws(
    websocket: WebSocket, token: Optional[str] = None
) -> Optional[User]:
    """
    Get current user from WebSocket token

    Args:
        websocket: WebSocket connection
        token: JWT token

    Returns:
        User or None
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")

        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        # Create a mock user object (in production, fetch from DB)
        user = User(id=int(user_id), username="", email="")
        return user

    except Exception as e:
        logger.error(f"WebSocket auth error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None


async def handle_chat_websocket(websocket: WebSocket, token: str):
    """
    Handle WebSocket chat connection

    Message format:
    {
        "type": "chat",
        "message": "User question",
        "conversation_id": 123,  // optional
        "temperature": 0.7,      // optional
        "max_tokens": 2048       // optional
    }

    Response format:
    {
        "type": "metadata",      // or "text", "done", "error"
        "content": "...",
        "sources": [...],
        "conversation_id": 123
    }
    """
    # Authenticate user
    user = await get_current_user_ws(websocket, token)
    if not user:
        return

    # Connect user
    await manager.connect(user.id, websocket)

    # Get database session
    db_generator = get_db()
    db = await anext(db_generator)

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            request = json.loads(data)

            message_type = request.get("type")

            if message_type == "chat":
                await handle_chat_message(websocket, request, user, db)
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                    }
                )

    except WebSocketDisconnect:
        manager.disconnect(user.id)
        logger.info(f"User {user.id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json(
            {"type": "error", "message": f"Server error: {str(e)}"}
        )
        manager.disconnect(user.id)
    finally:
        # Close database session
        try:
            await db.close()
        except Exception:
            pass


async def handle_chat_message(
    websocket: WebSocket, request: dict, user: User, db: AsyncSession
):
    """
    Handle chat message and stream response

    Args:
        websocket: WebSocket connection
        request: Chat request
        user: Current user
        db: Database session
    """
    try:
        message_text = request.get("message", "").strip()
        conversation_id = request.get("conversation_id")
        temperature = request.get("temperature", 0.7)
        max_tokens = request.get("max_tokens", 2048)

        if not message_text:
            await websocket.send_json(
                {"type": "error", "message": "Message cannot be empty"}
            )
            return

        # Get or create conversation
        if conversation_id:
            result = await db.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id, Conversation.user_id == user.id
                )
            )
            conversation = result.scalar_one_or_none()

            if not conversation:
                await websocket.send_json(
                    {"type": "error", "message": "Conversation not found"}
                )
                return
        else:
            # Create new conversation
            conversation = Conversation(title=message_text[:100], user_id=user.id)
            db.add(conversation)
            await db.flush()

        # Get conversation history
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at)
            .limit(10)
        )
        history_messages = result.scalars().all()

        conversation_history = [
            {"role": msg.role, "content": msg.content} for msg in history_messages
        ]

        # Create user message
        user_message = Message(
            conversation_id=conversation.id, role="user", content=message_text
        )
        db.add(user_message)
        await db.flush()

        # Stream RAG response
        full_response = ""
        sources = []
        retrieved_count = 0
        retrieval_time = 0.0
        generation_time = 0.0
        total_time = 0.0
        tokens_used = 0

        async for chunk in rag_service.query_stream(
            query=message_text,
            conversation_history=conversation_history,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            chunk_type = chunk.get("type")

            if chunk_type == "metadata":
                # Send metadata first
                sources = chunk.get("sources", [])
                retrieved_count = chunk.get("retrieved_count", 0)
                retrieval_time = chunk.get("retrieval_time", 0.0)

                await websocket.send_json(
                    {
                        "type": "metadata",
                        "sources": sources,
                        "retrieved_count": retrieved_count,
                        "retrieval_time": retrieval_time,
                        "conversation_id": conversation.id,
                    }
                )

            elif chunk_type == "text":
                # Stream text chunks
                content = chunk.get("content", "")
                full_response += content

                await websocket.send_json({"type": "text", "content": content})

            elif chunk_type == "done":
                # Final metadata
                generation_time = chunk.get("generation_time", 0.0)
                total_time = chunk.get("total_time", 0.0)
                tokens_used = chunk.get("tokens_used", 0)

                # Create assistant message
                assistant_message = Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=full_response.strip(),
                    sources=sources,
                    processing_time=total_time,
                    tokens_used=tokens_used,
                )
                db.add(assistant_message)

                # Update conversation
                conversation.last_message_at = datetime.utcnow()
                conversation.updated_at = datetime.utcnow()

                await db.commit()
                await db.refresh(assistant_message)

                # Send done message
                await websocket.send_json(
                    {
                        "type": "done",
                        "message_id": assistant_message.id,
                        "generation_time": generation_time,
                        "total_time": total_time,
                        "tokens_used": tokens_used,
                    }
                )

            elif chunk_type == "error":
                # Error occurred
                await websocket.send_json(
                    {"type": "error", "message": chunk.get("message", "Unknown error")}
                )
                await db.rollback()
                return

    except Exception as e:
        logger.error(f"Chat message handling error: {e}")
        await websocket.send_json(
            {"type": "error", "message": f"Failed to process message: {str(e)}"}
        )
        await db.rollback()
