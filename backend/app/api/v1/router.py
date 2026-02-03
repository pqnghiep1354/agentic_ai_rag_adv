"""
API v1 Router - aggregates all v1 endpoints
"""

from fastapi import APIRouter

from app.api.v1.endpoints import documents, chat, admin

api_router = APIRouter()

# Include all endpoint routers
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

# TODO: Add more routers as they are implemented
# api_router.include_router(search.router, prefix="/search", tags=["search"])
# api_router.include_router(export.router, prefix="/export", tags=["export"])
