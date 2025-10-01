"""FRADECT - Fraud Detection & Risk Management Platform"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from src.api import ecommerce, financial, project
from src.core.config import settings

app = FastAPI(
    title="FRADECT API",
    description="AI-Powered Risk Management & Fraud Detection Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ecommerce.router, prefix="/api/v1/ecommerce", tags=["E-Commerce"])
app.include_router(financial.router, prefix="/api/v1/financial", tags=["Financial"])
app.include_router(project.router, prefix="/api/v1/project", tags=["Project"])

# Metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/")
async def root():
    return {
        "service": "FRADECT",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/ready")
async def ready():
    # TODO: Add database and Redis connectivity checks
    return {"status": "ready"}
