"""API Routers package."""

from api.routers.datasources import router as datasources_router
from api.routers.demographics import router as demographics_router
from api.routers.network import router as network_router
from api.routers.overview import router as overview_router
from api.routers.rag import router as rag_router
from api.routers.sentiment import router as sentiment_router
from api.routers.trends import router as trends_router

__all__ = [
    "datasources_router",
    "demographics_router",
    "network_router",
    "overview_router",
    "rag_router",
    "sentiment_router",
    "trends_router",
]
