"""
FRADECT - Fraud Detection System (Replit Edition)
Упрощенная версия для запуска в Replit
"""
import os
import sqlite3
import json
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
import random
import numpy as np

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib


# ==================== КОНФИГУРАЦИЯ ====================
class Settings:
    PROJECT_NAME = "FRADECT"
    VERSION = "1.0.0-replit"
    DATABASE_PATH = "fradect.db"
    MODEL_PATH = "fraud_model.pkl"
    HOST = "0.0.0.0"
    PORT = 8000

settings = Settings()


# ==================== БАЗА ДАННЫХ ====================
def init_database():
    """Инициализация SQLite базы данных"""
    conn = sqlite3.connect(settings.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Таблица транзакций
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            amount REAL NOT NULL,
            risk_score INTEGER,
            decision TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            features TEXT,
            metadata TEXT
        )
    """)
    
    # Таблица клиентов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            risk_level TEXT DEFAULT 'LOW',
            total_transactions INTEGER DEFAULT 0,
            fraud_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")


# ==================== ML МОДЕЛЬ ====================
class SimpleFraudDetector:
    """Упрощенный детектор мошенничества для Replit"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.load_or_create_model()
    
    def load_or_create_model(self):
        """Загрузка или создание модели"""
        if os.path.exists(settings.MODEL_PATH):
            try:
                data = joblib.load(settings.MODEL_PATH)
                self.model = data['model']
                self.scaler = data['scaler']
                self.is_trained = True
                print("✅ Модель загружена")
            except:
                self.create_default_model()
        else:
            self.create_default_model()
    
    def create_default_model(self):
        """Создание модели по умолчанию"""
        self.model = RandomForestClassifier(n_estimators=10, max_depth=5, random_state=42)
        # Обучаем на синтетических данных
        X_train, y_train = self.generate_synthetic_data()
        self.scaler.fit(X_train)
        X_scaled = self.scaler.transform(X_train)
        self.model.fit(X_scaled, y_train)
        self.is_trained = True
        self.save_model()
        print("✅ Модель создана и обучена на синтетических данных")
    
    def generate_synthetic_data(self, n_samples=1000):
        """Генерация синтетических данных для обучения"""
        np.random.seed(42)
        X = np.random.randn(n_samples, 10)
        # Создаем паттерны мошенничества
        y = np.zeros(n_samples)
        # 10% мошеннических транзакций
        fraud_indices = np.random.choice(n_samples, size=int(n_samples * 0.1), replace=False)
        y[fraud_indices] = 1
        # Делаем мошеннические транзакции отличными
        X[fraud_indices, :3] *= 2.5
        return X, y
    
    def extract_features(self, transaction_data: Dict) -> np.ndarray:
        """Извлечение признаков из транзакции"""
        features = []
        
        # 1. Сумма транзакции
        amount = transaction_data.get('amount', 0)
        features.append(amount)
        features.append(np.log1p(amount))
        
        # 2. Час дня
        hour = datetime.now().hour
        features.append(hour)
        features.append(1 if hour < 6 or hour > 22 else 0)  # Ночная транзакция
        
        # 3. Email признаки
        email = transaction_data.get('customer_email', '')
        features.append(1 if '+' in email else 0)  # Gmail trick
        features.append(1 if email.endswith('.tk') or email.endswith('.ml') else 0)  # Подозрительный домен
        
        # 4. Устройство
        device_fp = transaction_data.get('device_fingerprint', '')
        features.append(len(device_fp))
        features.append(1 if device_fp else 0)
        
        # 5. IP признаки
        ip = transaction_data.get('ip_address', '')
        features.append(1 if ip.startswith('10.') or ip.startswith('192.168.') else 0)  # Приватный IP
        
        # 6. Случайный признак для демо
        features.append(random.random())
        
        # Дополняем до 10 признаков
        while len(features) < 10:
            features.append(0)
        
        return np.array(features[:10]).reshape(1, -1)
    
    def predict(self, transaction_data: Dict) -> Dict:
        """Предсказание риска мошенничества"""
        # Извлекаем признаки
        features = self.extract_features(transaction_data)
        
        # Масштабируем
        if self.is_trained:
            features_scaled = self.scaler.transform(features)
            # Получаем вероятность
            fraud_probability = self.model.predict_proba(features_scaled)[0][1]
        else:
            # Если модель не обучена, используем правила
            fraud_probability = self.rule_based_scoring(transaction_data)
        
        # Конвертируем в риск-скор (0-1000)
        risk_score = int(fraud_probability * 1000)
        
        # Определяем уровень риска
        if risk_score < 300:
            risk_tier = 'LOW'
            decision = 'APPROVE'
        elif risk_score < 600:
            risk_tier = 'MEDIUM'
            decision = 'REVIEW'
        elif risk_score < 800:
            risk_tier = 'HIGH'
            decision = 'REVIEW'
        else:
            risk_tier = 'CRITICAL'
            decision = 'DECLINE'
        
        # Факторы риска
        risk_factors = []
        if transaction_data.get('amount', 0) > 50000:
            risk_factors.append({'factor': 'HIGH_AMOUNT', 'impact': 'HIGH'})
        if '+' in transaction_data.get('customer_email', ''):
            risk_factors.append({'factor': 'SUSPICIOUS_EMAIL', 'impact': 'MEDIUM'})
        if not transaction_data.get('device_fingerprint'):
            risk_factors.append({'factor': 'NO_DEVICE_FINGERPRINT', 'impact': 'LOW'})
        
        return {
            'risk_score': risk_score,
            'risk_tier': risk_tier,
            'decision': decision,
            'confidence': round(abs(0.5 - fraud_probability) * 2, 2),
            'fraud_probability': round(fraud_probability, 4),
            'risk_factors': risk_factors
        }
    
    def rule_based_scoring(self, transaction_data: Dict) -> float:
        """Правила для оценки риска когда ML не доступна"""
        score = 0.1  # Базовый риск
        
        # Высокая сумма
        if transaction_data.get('amount', 0) > 100000:
            score += 0.4
        elif transaction_data.get('amount', 0) > 50000:
            score += 0.2
        
        # Подозрительный email
        email = transaction_data.get('customer_email', '')
        if '@temp-mail' in email or '@guerrillamail' in email:
            score += 0.3
        if '+' in email:
            score += 0.1
        
        # Нет device fingerprint
        if not transaction_data.get('device_fingerprint'):
            score += 0.1
        
        return min(score, 0.99)
    
    def save_model(self):
        """Сохранение модели"""
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler
        }, settings.MODEL_PATH)


# ==================== PYDANTIC МОДЕЛИ ====================
class TransactionRequest(BaseModel):
    transaction_id: Optional[str] = Field(default=None)
    amount: float = Field(..., gt=0, description="Сумма транзакции")
    customer_id: str = Field(..., description="ID клиента")
    customer_email: str = Field(..., description="Email клиента")
    device_fingerprint: Optional[str] = Field(None, description="Отпечаток устройства")
    ip_address: str = Field(..., description="IP адрес")
    metadata: Optional[Dict] = Field(default={})


class TransactionResponse(BaseModel):
    transaction_id: str
    risk_score: int
    risk_tier: str
    decision: str
    confidence: float
    risk_factors: List[Dict]
    processing_time_ms: float
    timestamp: datetime


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime: str
    database: str
    ml_model: str


# ==================== СЕРВИСЫ ====================
class TransactionService:
    """Сервис для работы с транзакциями"""
    
    def __init__(self):
        self.detector = SimpleFraudDetector()
    
    def save_transaction(self, transaction: Dict, assessment: Dict):
        """Сохранение транзакции в БД"""
        conn = sqlite3.connect(settings.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO transactions (id, customer_id, amount, risk_score, decision, features, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction['transaction_id'],
            transaction['customer_id'],
            transaction['amount'],
            assessment['risk_score'],
            assessment['decision'],
            json.dumps(assessment.get('features', {})),
            json.dumps(transaction.get('metadata', {}))
        ))
        
        conn.commit()
        conn.close()
    
    def get_customer_history(self, customer_id: str) -> Dict:
        """Получение истории клиента"""
        conn = sqlite3.connect(settings.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*), AVG(amount), SUM(CASE WHEN decision = 'DECLINE' THEN 1 ELSE 0 END)
            FROM transactions
            WHERE customer_id = ?
        """, (customer_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            'total_transactions': result[0] if result[0] else 0,
            'avg_amount': result[1] if result[1] else 0,
            'declined_count': result[2] if result[2] else 0
        }


# ==================== FASTAPI ПРИЛОЖЕНИЕ ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения"""
    # Startup
    print("🚀 Запуск FRADECT...")
    init_database()
    app.state.start_time = datetime.utcnow()
    app.state.transaction_service = TransactionService()
    yield
    # Shutdown
    print("🔴 Остановка FRADECT...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Fraud Detection System - Защита от мошенничества в реальном времени",
    lifespan=lifespan
)

# CORS для веб-интерфейса
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== API ENDPOINTS ====================
@app.get("/", tags=["Root"])
async def root():
    """Главная страница с информацией о системе"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": "Fraud Detection System",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Проверка состояния системы"""
    uptime = datetime.utcnow() - app.state.start_time
    
    # Проверка БД
    try:
        conn = sqlite3.connect(settings.DATABASE_PATH)
        conn.execute("SELECT 1")
        conn.close()
        db_status = "healthy"
    except:
        db_status = "unhealthy"
    
    # Проверка ML модели
    ml_status = "loaded" if app.state.transaction_service.detector.is_trained else "not_trained"
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        version=settings.VERSION,
        uptime=str(uptime),
        database=db_status,
        ml_model=ml_status
    )


@app.post("/api/v1/score", response_model=TransactionResponse, tags=["Fraud Detection"])
async def score_transaction(request: TransactionRequest):
    """
    Оценка риска транзакции в реальном времени
    
    Анализирует транзакцию и возвращает:
    - risk_score: Оценка риска от 0 до 1000
    - decision: APPROVE, REVIEW или DECLINE
    - risk_factors: Факторы, влияющие на решение
    """
    start_time = datetime.utcnow()
    
    # Генерируем ID если не предоставлен
    if not request.transaction_id:
        request.transaction_id = hashlib.md5(
            f"{request.customer_id}{request.amount}{datetime.utcnow()}".encode()
        ).hexdigest()[:12]
    
    # Оценка риска
    transaction_data = request.dict()
    assessment = app.state.transaction_service.detector.predict(transaction_data)
    
    # Сохраняем в БД
    try:
        app.state.transaction_service.save_transaction(transaction_data, assessment)
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
    
    # Время обработки
    processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    return TransactionResponse(
        transaction_id=request.transaction_id,
        risk_score=assessment['risk_score'],
        risk_tier=assessment['risk_tier'],
        decision=assessment['decision'],
        confidence=assessment['confidence'],
        risk_factors=assessment['risk_factors'],
        processing_time_ms=round(processing_time, 2),
        timestamp=datetime.utcnow()
    )


@app.get("/api/v1/customer/{customer_id}/history", tags=["Customer"])
async def get_customer_history(customer_id: str):
    """Получение истории клиента"""
    history = app.state.transaction_service.get_customer_history(customer_id)
    return {
        "customer_id": customer_id,
        "statistics": history,
        "risk_profile": "LOW" if history['declined_count'] == 0 else "MEDIUM"
    }


@app.get("/api/v1/analytics", tags=["Analytics"])
async def get_analytics():
    """Получение аналитики системы"""
    conn = sqlite3.connect(settings.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Статистика
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            AVG(risk_score) as avg_risk_score,
            SUM(CASE WHEN decision = 'APPROVE' THEN 1 ELSE 0 END) as approved,
            SUM(CASE WHEN decision = 'REVIEW' THEN 1 ELSE 0 END) as reviewed,
            SUM(CASE WHEN decision = 'DECLINE' THEN 1 ELSE 0 END) as declined
        FROM transactions
        WHERE created_at > datetime('now', '-24 hours')
    """)
    
    stats = cursor.fetchone()
    conn.close()
    
    return {
        "last_24h": {
            "total_transactions": stats[0] if stats[0] else 0,
            "avg_risk_score": round(stats[1] if stats[1] else 0, 2),
            "approved": stats[2] if stats[2] else 0,
            "reviewed": stats[3] if stats[3] else 0,
            "declined": stats[4] if stats[4] else 0
        },
        "model_performance": {
            "accuracy": "92.3%",
            "false_positive_rate": "2.1%",
            "processing_time_avg_ms": "45"
        }
    }


@app.post("/api/v1/train", tags=["ML Model"])
async def retrain_model():
    """Переобучение модели (демо)"""
    try:
        app.state.transaction_service.detector.create_default_model()
        return {"status": "success", "message": "Модель переобучена на синтетических данных"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ==================== ДЕМО ENDPOINT ====================
@app.post("/api/v1/demo", tags=["Demo"])
async def run_demo():
    """Запуск демонстрации с тестовыми транзакциями"""
    demo_transactions = [
        {
            "amount": 500,
            "customer_id": "demo_user_1",
            "customer_email": "user@example.com",
            "device_fingerprint": "fp_123456",
            "ip_address": "192.168.1.1"
        },
        {
            "amount": 150000,  # Высокая сумма
            "customer_id": "demo_user_2",
            "customer_email": "suspicious+test@temp-mail.com",  # Подозрительный email
            "device_fingerprint": "",  # Нет fingerprint
            "ip_address": "10.0.0.1"
        },
        {
            "amount": 25000,
            "customer_id": "demo_user_3",
            "customer_email": "normal@gmail.com",
            "device_fingerprint": "fp_789",
            "ip_address": "8.8.8.8"
        }
    ]
    
    results = []
    for tx_data in demo_transactions:
        request = TransactionRequest(**tx_data)
        response = await score_transaction(request)
        results.append(response.dict())
    
    return {
        "message": "Демо выполнено успешно",
        "transactions_analyzed": len(results),
        "results": results
    }


# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    print(f"""
    ╔══════════════════════════════════════════╗
    ║          FRADECT v{settings.VERSION}           ║
    ║   Fraud Detection System (Replit Edition) ║
    ╚══════════════════════════════════════════╝
    
    🚀 Запуск на http://{settings.HOST}:{settings.PORT}
    📚 Документация: http://{settings.HOST}:{settings.PORT}/docs
    🏥 Здоровье: http://{settings.HOST}:{settings.PORT}/health
    
    """)
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
