"""
Конфигурация базы данных и подключения
"""
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from contextlib import asynccontextmanager
import redis.asyncio as redis

from src.core.config import settings
from src.core.models import Base


# Синхронный движок для миграций
engine = create_engine(
    settings.DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://'),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG
)

# Асинхронный движок для приложения
async_engine = create_async_engine(
    settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'),
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=40,
    echo=settings.DEBUG
)

# Фабрики сессий
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Redis клиент
redis_client: Optional[redis.Redis] = None


async def init_db():
    """Инициализация базы данных"""
    async with async_engine.begin() as conn:
        # Создаем все таблицы
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ База данных инициализирована")


async def init_redis():
    """Инициализация Redis"""
    global redis_client
    
    redis_client = await redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50
    )
    
    # Проверка подключения
    try:
        await redis_client.ping()
        print("✅ Redis подключен")
    except Exception as e:
        print(f"❌ Ошибка подключения к Redis: {e}")
        redis_client = None


async def close_redis():
    """Закрытие подключения к Redis"""
    global redis_client
    
    if redis_client:
        await redis_client.close()
        redis_client = None
        print("✅ Redis отключен")


def get_db() -> Session:
    """Dependency для получения синхронной сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для получения асинхронной сессии БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_redis() -> redis.Redis:
    """Dependency для получения Redis клиента"""
    if not redis_client:
        raise RuntimeError("Redis не инициализирован")
    return redis_client


@asynccontextmanager
async def database_session():
    """Context manager для работы с БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class DatabaseManager:
    """Менеджер для работы с базой данных"""
    
    def __init__(self):
        self.engine = async_engine
        self.session_factory = AsyncSessionLocal
        self._redis_client = None
    
    async def connect(self):
        """Подключение к БД и Redis"""
        await init_db()
        await init_redis()
        self._redis_client = redis_client
    
    async def disconnect(self):
        """Отключение от БД и Redis"""
        await self.engine.dispose()
        await close_redis()
    
    @asynccontextmanager
    async def session(self):
        """Получение сессии БД"""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    @property
    def redis(self) -> redis.Redis:
        """Получение Redis клиента"""
        if not self._redis_client:
            raise RuntimeError("Redis не подключен")
        return self._redis_client
    
    async def health_check(self) -> dict:
        """Проверка состояния БД и Redis"""
        status = {
            "database": "unhealthy",
            "redis": "unhealthy",
            "details": {}
        }
        
        # Проверка БД
        try:
            async with self.session() as session:
                await session.execute("SELECT 1")
            status["database"] = "healthy"
        except Exception as e:
            status["details"]["database_error"] = str(e)
        
        # Проверка Redis
        try:
            if self._redis_client:
                await self._redis_client.ping()
                status["redis"] = "healthy"
        except Exception as e:
            status["details"]["redis_error"] = str(e)
        
        return status


# Глобальный экземпляр менеджера
db_manager = DatabaseManager()
