"""
API v1 Router - aggregates all v1 endpoints
"""

from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, chat, documents

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"],
)

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"],
)

api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["chat"],
)

api_router.include_router(
    admin.router,
    tags=["admin"],
)
