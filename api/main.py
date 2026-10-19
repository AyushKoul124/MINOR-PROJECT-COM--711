"""FastAPI Application Main Entrypoint.

AI-Driven Social Media Audience Intelligence Framework
Academic Research Testbed (NTRO Problem Statement Inspiration) | Dec 2026 Viva
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import (
    datasources_router,
    demographics_router,
    network_router,
    overview_router,
    rag_router,
    sentiment_router,
    trends_router,
)

logger = logging.getLogger("api.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SOCMINT Intelligence API Server...")
    yield
    logger.info("Shutting down SOCMINT Intelligence API Server...")


app = FastAPI(
    title="AI-Driven Social Media Audience Intelligence Framework API",
    description=(
        "Academic Research Prototype & SOCMINT Analytics Backend. "
        "Provides multi-dialectal sentiment analysis, heuristic demographic profiling (k >= 50), "
        "BERTopic trend velocity calculations, Louvain network partitioning, advisory CIB anomaly screening, "
        "and grounded pgvector RAG intelligence query endpoints."
    ),
    version="4.8.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration for React 18 frontend (Vite dev port 5173 / prod port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under /api prefix
app.include_router(overview_router, prefix="/api")
app.include_router(sentiment_router, prefix="/api")
app.include_router(demographics_router, prefix="/api")
app.include_router(trends_router, prefix="/api")
app.include_router(network_router, prefix="/api")
app.include_router(rag_router, prefix="/api")
app.include_router(datasources_router, prefix="/api")


@app.get("/", tags=["Root"])
def root_status():
    return JSONResponse(
        content={
            "name": "AI-Driven Social Media Audience Intelligence Framework",
            "prototype": "Academic Research Testbed (NTRO Inspiration Only)",
            "status": "online",
            "api_docs": "/docs",
            "endpoints": [
                "/api/health",
                "/api/overview",
                "/api/sentiment/timeline",
                "/api/demographics",
                "/api/trends",
                "/api/network/graph",
                "/api/rag/query",
                "/api/datasources",
                "/api/orchestrator/trigger",
            ],
        }
    )
