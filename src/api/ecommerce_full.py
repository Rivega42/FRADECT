"""
API endpoints для модуля электронной коммерции
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from src.core.models import RiskScore, Decision
from src.services.fraud_detector import FraudDetector
from src.services.feature_extractor import FeatureExtractor
from src.core.database import get_db

router = APIRouter()

# Инициализация сервисов
fraud_detector = FraudDetector()
feature_extractor = FeatureExtractor()


class TransactionRequest(BaseModel):
    """Модель запроса для оценки транзакции"""
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    amount: float = Field(..., gt=0, description="Сумма транзакции")
    currency: str = Field(default="RUB", description="Валюта")
    customer_id: str = Field(..., description="ID клиента")
    customer_email: str = Field(..., description="Email клиента")
    customer_phone: Optional[str] = Field(None, description="Телефон клиента")
    device_fingerprint: Optional[str] = Field(None, description="Отпечаток устройства")
    ip_address: str = Field(..., description="IP адрес")
    user_agent: Optional[str] = Field(None, description="User-Agent браузера")
    shipping_address: Optional[Dict[str, Any]] = Field(None, description="Адрес доставки")
    billing_address: Optional[Dict[str, Any]] = Field(None, description="Адрес плательщика")
    items: Optional[list] = Field(None, description="Список товаров")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Дополнительные данные")


class TransactionResponse(BaseModel):
    """Модель ответа оценки транзакции"""
    transaction_id: str
    risk_score: int = Field(..., ge=0, le=1000, description="Оценка риска (0-1000)")
    risk_tier: str = Field(..., description="Уровень риска: LOW/MEDIUM/HIGH/CRITICAL")
    decision: str = Field(..., description="Решение: APPROVE/REVIEW/DECLINE")
    confidence: float = Field(..., ge=0, le=1, description="Уверенность в решении")
    expected_loss: Optional[float] = Field(None, description="Ожидаемая потеря")
    risk_factors: list = Field(..., description="Факторы риска")
    suggested_actions: list = Field(..., description="Рекомендуемые действия")
    processing_time_ms: float = Field(..., description="Время обработки в мс")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReturnRequest(BaseModel):
    """Модель запроса на возврат"""
    customer_id: str
    order_id: str
    items: list
    reason: str
    return_amount: float
    days_since_purchase: int


class PromoAbuseCheck(BaseModel):
    """Модель проверки злоупотребления промокодами"""
    customer_id: str
    promo_code: str
    device_fingerprint: str
    email: str
    phone: Optional[str]
    ip_address: str


@router.post("/score", response_model=TransactionResponse)
async def score_transaction(
    request: TransactionRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """
    Оценка риска транзакции в реальном времени
    
    - **amount**: Сумма транзакции
    - **customer_id**: Идентификатор клиента
    - **device_fingerprint**: Отпечаток устройства для обнаружения мультиаккаунтов
    - **ip_address**: IP для геолокации и проверки прокси
    
    Возвращает оценку риска и рекомендацию по действию.
    """
    start_time = datetime.utcnow()
    
    try:
        # Извлечение признаков
        features = await feature_extractor.extract_transaction_features(
            transaction_data=request.dict(),
            customer_id=request.customer_id,
            db=db
        )
        
        # Оценка риска
        risk_assessment = await fraud_detector.assess_transaction(
            features=features,
            amount=request.amount
        )
        
        # Сохранение в БД (асинхронно)
        background_tasks.add_task(
            save_transaction_assessment,
            request.dict(),
            risk_assessment,
            db
        )
        
        # Вычисление времени обработки
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return TransactionResponse(
            transaction_id=request.transaction_id,
            risk_score=risk_assessment['score'],
            risk_tier=risk_assessment['tier'],
            decision=risk_assessment['decision'],
            confidence=risk_assessment['confidence'],
            expected_loss=risk_assessment.get('expected_loss'),
            risk_factors=risk_assessment['factors'],
            suggested_actions=risk_assessment['actions'],
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/return-abuse/check")
async def check_return_abuse(request: ReturnRequest, db=Depends(get_db)):
    """
    Проверка на злоупотребление возвратами
    
    Анализирует историю возвратов клиента и определяет вероятность
    злоупотребления (вардробинг, серийные возвраты).
    """
    # Получение истории клиента
    customer_history = await get_customer_return_history(
        request.customer_id, 
        db
    )
    
    # Анализ паттернов
    abuse_indicators = {
        'return_rate': calculate_return_rate(customer_history),
        'avg_days_to_return': calculate_avg_return_time(customer_history),
        'high_value_returns': count_high_value_returns(customer_history),
        'seasonal_pattern': detect_seasonal_abuse(customer_history),
        'serial_returner': is_serial_returner(customer_history)
    }
    
    # Вычисление оценки злоупотребления
    abuse_score = calculate_abuse_score(abuse_indicators)
    
    return {
        'customer_id': request.customer_id,
        'order_id': request.order_id,
        'abuse_score': abuse_score,
        'classification': classify_return_behavior(abuse_score),
        'recommendation': get_return_recommendation(abuse_score),
        'indicators': abuse_indicators,
        'actions': suggest_return_actions(abuse_score, request.return_amount)
    }


@router.post("/promo-abuse/detect")
async def detect_promo_abuse(request: PromoAbuseCheck, db=Depends(get_db)):
    """
    Обнаружение злоупотребления промокодами
    
    Проверяет использование промокодов на предмет создания
    множественных аккаунтов и других видов мошенничества.
    """
    # Проверка устройства
    device_accounts = await get_accounts_by_device(
        request.device_fingerprint, 
        db
    )
    
    # Проверка email паттернов
    email_variants = detect_email_variants(request.email, db)
    
    # Проверка IP
    ip_accounts = await get_accounts_by_ip(request.ip_address, db)
    
    # Анализ злоупотребления
    abuse_signals = {
        'multiple_accounts_same_device': len(device_accounts) > 1,
        'email_pattern_detected': len(email_variants) > 0,
        'multiple_accounts_same_ip': len(ip_accounts) > 2,
        'promo_code_velocity': await check_promo_velocity(request.promo_code, db),
        'account_age_suspicious': await is_new_account_abuse(request.customer_id, db)
    }
    
    risk_level = calculate_promo_abuse_risk(abuse_signals)
    
    return {
        'customer_id': request.customer_id,
        'promo_code': request.promo_code,
        'risk_level': risk_level,
        'abuse_detected': risk_level > 0.7,
        'signals': abuse_signals,
        'linked_accounts': {
            'by_device': device_accounts,
            'by_email_pattern': email_variants,
            'by_ip': ip_accounts
        },
        'recommendation': 'BLOCK' if risk_level > 0.7 else 'ALLOW',
        'suggested_actions': get_promo_abuse_actions(risk_level)
    }


@router.get("/customer/{customer_id}/risk-profile")
async def get_customer_risk_profile(customer_id: str, db=Depends(get_db)):
    """
    Получение полного профиля риска клиента
    
    Объединяет данные по всем типам рисков для создания
    комплексной оценки клиента.
    """
    # Сбор данных из всех источников
    transaction_history = await get_transaction_history(customer_id, db)
    return_history = await get_customer_return_history(customer_id, db)
    promo_usage = await get_promo_usage_history(customer_id, db)
    
    # Расчет метрик
    profile = {
        'customer_id': customer_id,
        'fraud_risk': {
            'score': calculate_fraud_risk_score(transaction_history),
            'total_transactions': len(transaction_history),
            'declined_transactions': count_declined(transaction_history),
            'chargebacks': count_chargebacks(transaction_history)
        },
        'return_abuse_risk': {
            'score': calculate_return_abuse_score(return_history),
            'return_rate': calculate_return_rate(return_history),
            'total_returns': len(return_history),
            'classification': classify_return_behavior(return_history)
        },
        'promo_abuse_risk': {
            'score': calculate_promo_risk_score(promo_usage),
            'codes_used': len(promo_usage),
            'suspicious_patterns': detect_promo_patterns(promo_usage)
        },
        'overall_risk': 'CALCULATE_WEIGHTED_AVERAGE',
        'customer_lifetime_value': calculate_clv(customer_id, db),
        'recommendations': generate_customer_recommendations(profile),
        'last_updated': datetime.utcnow()
    }
    
    return profile


@router.get("/analytics/summary")
async def get_analytics_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db=Depends(get_db)
):
    """
    Получение аналитической сводки по модулю
    """
    # Установка дат по умолчанию (последние 30 дней)
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    stats = await calculate_module_statistics(start_date, end_date, db)
    
    return {
        'period': {
            'start': start_date,
            'end': end_date
        },
        'transactions': {
            'total': stats['total_transactions'],
            'approved': stats['approved'],
            'declined': stats['declined'],
            'reviewed': stats['reviewed']
        },
        'fraud_prevention': {
            'fraud_prevented_amount': stats['fraud_prevented_amount'],
            'fraud_prevented_count': stats['fraud_prevented_count'],
            'false_positive_rate': stats['false_positive_rate'],
            'precision': stats['precision'],
            'recall': stats['recall']
        },
        'returns': {
            'total_returns': stats['total_returns'],
            'abuse_detected': stats['return_abuse_detected'],
            'money_saved': stats['return_abuse_savings']
        },
        'promo_abuse': {
            'attempts_blocked': stats['promo_abuse_blocked'],
            'multi_accounts_detected': stats['multi_accounts_detected'],
            'savings': stats['promo_abuse_savings']
        },
        'performance': {
            'avg_response_time_ms': stats['avg_response_time'],
            'uptime_percent': stats['uptime'],
            'api_calls': stats['total_api_calls']
        }
    }


# Вспомогательные функции (заглушки - нужна реальная реализация)
async def save_transaction_assessment(transaction_data, assessment, db):
    """Сохранение результатов оценки в БД"""
    pass

async def get_customer_return_history(customer_id, db):
    """Получение истории возвратов клиента"""
    return []

def calculate_return_rate(history):
    """Расчет процента возвратов"""
    return 0.0

def calculate_avg_return_time(history):
    """Расчет среднего времени до возврата"""
    return 0.0

def count_high_value_returns(history):
    """Подсчет возвратов дорогих товаров"""
    return 0

def detect_seasonal_abuse(history):
    """Обнаружение сезонных паттернов злоупотребления"""
    return False

def is_serial_returner(history):
    """Определение серийного возвратчика"""
    return False

def calculate_abuse_score(indicators):
    """Расчет оценки злоупотребления"""
    return 0

def classify_return_behavior(score):
    """Классификация поведения возвратов"""
    return "NORMAL"

def get_return_recommendation(score):
    """Получение рекомендации по возврату"""
    return "APPROVE"

def suggest_return_actions(score, amount):
    """Предложение действий по возврату"""
    return []

async def get_accounts_by_device(fingerprint, db):
    """Получение аккаунтов по отпечатку устройства"""
    return []

def detect_email_variants(email, db):
    """Обнаружение вариантов email"""
    return []

async def get_accounts_by_ip(ip, db):
    """Получение аккаунтов по IP"""
    return []

async def check_promo_velocity(code, db):
    """Проверка скорости использования промокода"""
    return 0

async def is_new_account_abuse(customer_id, db):
    """Проверка злоупотребления новым аккаунтом"""
    return False

def calculate_promo_abuse_risk(signals):
    """Расчет риска злоупотребления промокодами"""
    return 0.0

def get_promo_abuse_actions(risk_level):
    """Получение действий при злоупотреблении промокодами"""
    return []

from datetime import timedelta

async def get_transaction_history(customer_id, db):
    """Получение истории транзакций"""
    return []

async def get_promo_usage_history(customer_id, db):
    """Получение истории использования промокодов"""
    return []

def calculate_fraud_risk_score(history):
    """Расчет оценки риска мошенничества"""
    return 0

def count_declined(history):
    """Подсчет отклоненных транзакций"""
    return 0

def count_chargebacks(history):
    """Подсчет чарджбэков"""
    return 0

def calculate_return_abuse_score(history):
    """Расчет оценки злоупотребления возвратами"""
    return 0

def calculate_promo_risk_score(usage):
    """Расчет риска злоупотребления промокодами"""
    return 0

def detect_promo_patterns(usage):
    """Обнаружение паттернов использования промо"""
    return []

def calculate_clv(customer_id, db):
    """Расчет пожизненной ценности клиента"""
    return 0.0

def generate_customer_recommendations(profile):
    """Генерация рекомендаций для клиента"""
    return []

async def calculate_module_statistics(start_date, end_date, db):
    """Расчет статистики модуля"""
    return {
        'total_transactions': 0,
        'approved': 0,
        'declined': 0,
        'reviewed': 0,
        'fraud_prevented_amount': 0,
        'fraud_prevented_count': 0,
        'false_positive_rate': 0,
        'precision': 0,
        'recall': 0,
        'total_returns': 0,
        'return_abuse_detected': 0,
        'return_abuse_savings': 0,
        'promo_abuse_blocked': 0,
        'multi_accounts_detected': 0,
        'promo_abuse_savings': 0,
        'avg_response_time': 0,
        'uptime': 99.9,
        'total_api_calls': 0
    }
