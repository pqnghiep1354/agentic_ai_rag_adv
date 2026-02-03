"""
Unit tests for domain models
"""

import pytest
from datetime import datetime

from app.models.domain.user import User
from app.models.domain.document import Document, DocumentStatus
from app.models.domain.conversation import Conversation, Message


class TestUserModel:
    """Tests for User model"""

    def test_user_repr(self):
        """Test User string representation"""
        user = User(id=1, email="test@example.com", username="testuser", hashed_password="hash")
        repr_str = repr(user)

        assert "User" in repr_str
        assert "id=1" in repr_str
        assert "test@example.com" in repr_str
        assert "testuser" in repr_str

    def test_user_attributes(self):
        """Test User model has expected attributes"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hash",
            is_active=True,
            is_superuser=False,
        )

        # When explicitly set, values should be correct
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.email == "test@example.com"


class TestDocumentModel:
    """Tests for Document model"""

    def test_document_repr(self):
        """Test Document string representation"""
        doc = Document(
            id=1,
            title="Test Document",
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="pdf",
            file_size=1024,
            owner_id=1,
        )
        repr_str = repr(doc)

        assert "Document" in repr_str
        assert "id=1" in repr_str
        assert "Test Document" in repr_str

    def test_document_with_status(self):
        """Test Document with explicit status"""
        doc = Document(
            title="Test",
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="pdf",
            file_size=1024,
            owner_id=1,
            status=DocumentStatus.PENDING,
        )

        assert doc.status == DocumentStatus.PENDING


class TestDocumentStatus:
    """Tests for DocumentStatus enum"""

    def test_status_values(self):
        """Test DocumentStatus enum values"""
        assert DocumentStatus.PENDING.value == "pending"
        assert DocumentStatus.PROCESSING.value == "processing"
        assert DocumentStatus.COMPLETED.value == "completed"
        assert DocumentStatus.FAILED.value == "failed"

    def test_status_is_string_enum(self):
        """Test DocumentStatus inherits from str"""
        assert isinstance(DocumentStatus.PENDING, str)
        assert DocumentStatus.PENDING == "pending"


class TestConversationModel:
    """Tests for Conversation model"""

    def test_conversation_message_count_empty(self):
        """Test message count when no messages"""
        conv = Conversation(id=1, title="Test", user_id=1)
        conv.messages = []

        assert conv.message_count == 0

    def test_conversation_message_count_with_messages(self):
        """Test message count with messages"""
        conv = Conversation(id=1, title="Test", user_id=1)
        conv.messages = [
            Message(id=1, conversation_id=1, role="user", content="Hello"),
            Message(id=2, conversation_id=1, role="assistant", content="Hi there"),
        ]

        assert conv.message_count == 2

    def test_conversation_default_messages(self):
        """Test conversation with empty messages list"""
        conv = Conversation(id=1, title="Test", user_id=1)
        # Messages defaults to empty relationship list
        conv.messages = []

        assert conv.message_count == 0


class TestMessageModel:
    """Tests for Message model"""

    def test_message_roles(self):
        """Test valid message roles"""
        user_msg = Message(conversation_id=1, role="user", content="Hello")
        assistant_msg = Message(conversation_id=1, role="assistant", content="Hi")
        system_msg = Message(conversation_id=1, role="system", content="You are helpful")

        assert user_msg.role == "user"
        assert assistant_msg.role == "assistant"
        assert system_msg.role == "system"

    def test_message_optional_fields(self):
        """Test message optional fields default to None"""
        msg = Message(conversation_id=1, role="user", content="Hello")

        assert msg.sources is None
        assert msg.retrieved_chunks is None
        assert msg.retrieval_score is None
        assert msg.processing_time is None
        assert msg.tokens_used is None
        assert msg.feedback_rating is None
        assert msg.feedback_comment is None

    def test_message_with_sources(self):
        """Test message with sources JSON"""
        sources = [
            {"document_id": 1, "title": "Doc 1", "page": 5},
            {"document_id": 2, "title": "Doc 2", "page": 10},
        ]
        msg = Message(
            conversation_id=1,
            role="assistant",
            content="Based on the documents...",
            sources=sources,
        )

        assert msg.sources == sources
        assert len(msg.sources) == 2

    def test_message_with_metrics(self):
        """Test message with performance metrics"""
        msg = Message(
            conversation_id=1,
            role="assistant",
            content="Response",
            retrieval_score=0.85,
            processing_time=1.5,
            tokens_used=256,
        )

        assert msg.retrieval_score == 0.85
        assert msg.processing_time == 1.5
        assert msg.tokens_used == 256

    def test_message_with_feedback(self):
        """Test message with user feedback"""
        msg = Message(
            conversation_id=1,
            role="assistant",
            content="Response",
            feedback_rating=5,
            feedback_comment="Very helpful!",
        )

        assert msg.feedback_rating == 5
        assert msg.feedback_comment == "Very helpful!"
