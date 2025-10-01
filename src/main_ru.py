"""FRADECT - Платформа обнаружения мошенничества и управления рисками"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from src.api import ecommerce, financial, project
from src.core.config import settings

app = FastAPI(
    title="FRADECT API",
    description="Платформа управления рисками и обнаружения мошенничества на базе ИИ",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(ecommerce.router, prefix="/api/v1/ecommerce", tags=["Электронная коммерция"])
app.include_router(financial.router, prefix="/api/v1/financial", tags=["Финансы"])
app.include_router(project.router, prefix="/api/v1/project", tags=["Проекты"])

# Эндпоинт метрик
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/")
async def root():
    """Корневой эндпоинт для проверки работоспособности"""
    return {
        "service": "FRADECT",
        "version": "0.1.0",
        "status": "работает",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Проверка здоровья сервиса"""
    return {"status": "исправен"}


@app.get("/ready")
async def ready():
    """Проверка готовности сервиса"""
    # TODO: Добавить проверку подключения к базе данных и Redis
    return {"status": "готов"}
