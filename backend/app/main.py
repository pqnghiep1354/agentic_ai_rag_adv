"""
Main FastAPI application
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.api.websockets.chat_ws import handle_chat_websocket
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for startup and shutdown
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("Initializing database connections...")

    # Initialize database connection pool and create tables
    try:
        from app.core.database import engine
        from app.models.domain import conversation, document, user  # noqa: F401 - ensure models are registered

        from sqlalchemy import text

        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

    # Create Qdrant collections if not exist
    try:
        from app.repositories.vector_repo import get_vector_repository

        vector_repo = get_vector_repository()
        vector_repo.create_collection(recreate=False)
        logger.info("Qdrant collection ready")
    except Exception as e:
        logger.warning(f"Qdrant initialization warning: {e}")

    # Verify Neo4j connection
    try:
        from app.repositories.graph_repo import get_graph_repository

        graph_repo = get_graph_repository()
        graph_repo.get_graph_stats()
        logger.info("Neo4j connection verified")
    except Exception as e:
        logger.warning(f"Neo4j connection warning: {e}")

    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Close Neo4j connection
    try:
        from app.repositories.graph_repo import _graph_repo

        if _graph_repo is not None:
            _graph_repo.close()
    except Exception as e:
        logger.warning(f"Neo4j shutdown warning: {e}")

    # Close database engine
    try:
        from app.core.database import engine

        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.warning(f"Database shutdown warning: {e}")

    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Agentic AI system with GraphRAG for Vietnamese Environmental Law Q&A",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information
    """
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs" if settings.DEBUG else "disabled",
        "health_check": "/health",
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors"""
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Resource not found"})


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Include API routers
app.include_router(api_router, prefix="/api/v1")


# WebSocket endpoint for chat streaming


@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket endpoint for real-time chat streaming

    Query params:
        token: JWT access token for authentication
    """
    await handle_chat_websocket(websocket, token)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
