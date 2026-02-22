"""Main entry point for the FastAPI application."""

from fastapi import FastAPI
from app.api.routes import router
from app.tools import initialize_tools
from app.core.logging import logger

# Initialize tools on startup
initialize_tools()

app = FastAPI(
    title="Agentic AI System",
    description="Production-style agentic AI system with planning and execution",
    version="0.1.0"
)

# Include API routes
app.include_router(router)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "agentic-ai-system"}


@app.get("/")
def root():
    """Root endpoint with API documentation info."""
    return {
        "service": "Agentic AI System",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "running"
    }


@app.on_event("startup")
async def startup_event():
    """Called on application startup."""
    logger.info("Agentic AI System starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    """Called on application shutdown."""
    logger.info("Agentic AI System shutting down...")