"""
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import router as api_router

# Create FastAPI instance
app = FastAPI(
    title="LINE Group RAG System",
    description="RAG system for LINE group chat analysis",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "LINE Group RAG System API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
