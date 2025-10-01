"""
Модели базы данных для FRADECT
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, ForeignKey, Enum, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

Base = declarative_base()


class RiskTier(enum.Enum):
    """Уровни риска"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Decision(enum.Enum):
    """Решения по транзакциям"""
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    DECLINE = "DECLINE"


class TransactionStatus(enum.Enum):
    """Статусы транзакций"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    REVIEWED = "REVIEWED"
    COMPLETED = "COMPLETED"
    REFUNDED = "REFUNDED"
    CHARGEBACK = "CHARGEBACK"


class Customer(Base):
    """Модель клиента"""
    __tablename__ = "customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(255), unique=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    
    # Риск-метрики
    fraud_score = Column(Integer, default=0)
    risk_tier = Column(Enum(RiskTier), default=RiskTier.LOW)
    return_abuse_score = Column(Integer, default=0)
    promo_abuse_score = Column(Integer, default=0)
    
    # Статистика
    total_orders = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    total_returns = Column(Integer, default=0)
    total_chargebacks = Column(Integer, default=0)
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_order_at = Column(DateTime)
    
    # Метаданные
    metadata = Column(JSON, default={})
    tags = Column(JSON, default=[])
    
    # Связи
    transactions = relationship("Transaction", back_populates="customer")
    devices = relationship("Device", secondary="customer_devices", back_populates="customers")
    addresses = relationship("Address", back_populates="customer")
    risk_decisions = relationship("RiskDecision", back_populates="customer")
    
    # Индексы
    __table_args__ = (
        Index('idx_customer_risk', 'risk_tier', 'fraud_score'),
        Index('idx_customer_created', 'created_at'),
    )


class Transaction(Base):
    """Модель транзакции"""
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(255), unique=True, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id'), nullable=False)
    
    # Финансовые данные
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default='RUB')
    payment_method = Column(String(50))
    
    # Статус и решение
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    risk_score = Column(Integer)
    risk_tier = Column(Enum(RiskTier))
    decision = Column(Enum(Decision))
    decision_reason = Column(String(500))
    
    # Данные устройства и сессии
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.id'))
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    session_id = Column(String(255))
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime)
    
    # Метаданные
    metadata = Column(JSON, default={})
    risk_factors = Column(JSON, default=[])
    
    # Связи
    customer = relationship("Customer", back_populates="transactions")
    device = relationship("Device", back_populates="transactions")
    items = relationship("TransactionItem", back_populates="transaction")
    
    # Индексы
    __table_args__ = (
        Index('idx_transaction_customer', 'customer_id', 'created_at'),
        Index('idx_transaction_status', 'status', 'risk_tier'),
        Index('idx_transaction_created', 'created_at'),
    )


class Device(Base):
    """Модель устройства"""
    __tablename__ = "devices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fingerprint = Column(String(255), unique=True, index=True, nullable=False)
    
    # Характеристики устройства
    device_type = Column(String(50))  # mobile, desktop, tablet
    os = Column(String(50))
    browser = Column(String(50))
    
    # Риск-метрики
    risk_score = Column(Integer, default=0)
    is_blacklisted = Column(Boolean, default=False)
    fraud_count = Column(Integer, default=0)
    
    # Временные метки
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    # Метаданные
    metadata = Column(JSON, default={})
    
    # Связи
    customers = relationship("Customer", secondary="customer_devices", back_populates="devices")
    transactions = relationship("Transaction", back_populates="device")


class CustomerDevice(Base):
    """Связь клиент-устройство"""
    __tablename__ = "customer_devices"
    
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id'), primary_key=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.id'), primary_key=True)
    first_used = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, default=datetime.utcnow)
    usage_count = Column(Integer, default=1)


class Address(Base):
    """Модель адреса"""
    __tablename__ = "addresses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id'), nullable=False)
    
    # Адресные данные
    address_type = Column(String(20))  # billing, shipping
    street = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(2))
    
    # Геоданные
    latitude = Column(Float)
    longitude = Column(Float)
    
    # Риск-метрики
    risk_score = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)
    delivery_success_rate = Column(Float)
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    
    # Связи
    customer = relationship("Customer", back_populates="addresses")
    
    # Индексы
    __table_args__ = (
        Index('idx_address_customer', 'customer_id'),
        Index('idx_address_location', 'city', 'country'),
    )


class RiskDecision(Base):
    """Модель решения по рискам"""
    __tablename__ = "risk_decisions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Сущность для оценки
    entity_type = Column(String(50))  # transaction, customer, project
    entity_id = Column(UUID(as_uuid=True))
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id'))
    
    # Оценка риска
    score = Column(Integer, nullable=False)
    tier = Column(Enum(RiskTier), nullable=False)
    decision = Column(Enum(Decision), nullable=False)
    confidence = Column(Float)
    
    # Детали решения
    factors = Column(JSON, default=[])
    model_version = Column(String(50))
    processing_time_ms = Column(Float)
    
    # Результат (для обучения)
    outcome = Column(String(50))  # confirmed_fraud, false_positive, true_negative
    outcome_updated_at = Column(DateTime)
    feedback = Column(JSON)
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    customer = relationship("Customer", back_populates="risk_decisions")
    
    # Индексы
    __table_args__ = (
        Index('idx_decision_entity', 'entity_type', 'entity_id'),
        Index('idx_decision_created', 'created_at'),
        Index('idx_decision_outcome', 'outcome', 'created_at'),
    )


class TransactionItem(Base):
    """Модель товара в транзакции"""
    __tablename__ = "transaction_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey('transactions.id'), nullable=False)
    
    # Данные товара
    product_id = Column(String(255))
    product_name = Column(String(500))
    category = Column(String(100))
    quantity = Column(Integer, default=1)
    price = Column(Float)
    
    # Статус
    is_returned = Column(Boolean, default=False)
    return_date = Column(DateTime)
    return_reason = Column(String(500))
    
    # Связи
    transaction = relationship("Transaction", back_populates="items")


class PromoCode(Base):
    """Модель промокода"""
    __tablename__ = "promo_codes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, index=True, nullable=False)
    
    # Параметры промокода
    discount_type = Column(String(20))  # percentage, fixed
    discount_value = Column(Float)
    min_purchase = Column(Float)
    max_uses = Column(Integer)
    max_uses_per_customer = Column(Integer, default=1)
    
    # Статус
    is_active = Column(Boolean, default=True)
    current_uses = Column(Integer, default=0)
    
    # Временные рамки
    valid_from = Column(DateTime)
    valid_until = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    usages = relationship("PromoUsage", back_populates="promo_code")


class PromoUsage(Base):
    """Модель использования промокода"""
    __tablename__ = "promo_usages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    promo_code_id = Column(UUID(as_uuid=True), ForeignKey('promo_codes.id'), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id'), nullable=False)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey('transactions.id'))
    
    # Данные использования
    device_fingerprint = Column(String(255))
    ip_address = Column(String(45))
    
    # Риск
    is_abuse = Column(Boolean, default=False)
    abuse_type = Column(String(50))  # multi_account, velocity, pattern
    
    # Временная метка
    used_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    promo_code = relationship("PromoCode", back_populates="usages")
    
    # Индексы
    __table_args__ = (
        Index('idx_promo_usage', 'promo_code_id', 'customer_id'),
        Index('idx_promo_device', 'device_fingerprint'),
    )


class MLModel(Base):
    """Модель машинного обучения"""
    __tablename__ = "ml_models"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    module = Column(String(50))  # ecommerce, financial, project
    
    # Параметры модели
    model_type = Column(String(50))  # xgboost, lightgbm, neural_net
    parameters = Column(JSON)
    features = Column(JSON)
    
    # Метрики
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    auc_roc = Column(Float)
    
    # Статус
    is_active = Column(Boolean, default=False)
    is_production = Column(Boolean, default=False)
    
    # Пути к файлам
    model_path = Column(String(500))
    artifacts_path = Column(String(500))
    
    # Временные метки
    trained_at = Column(DateTime)
    deployed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Индексы
    __table_args__ = (
        Index('idx_model_active', 'module', 'is_active'),
        Index('idx_model_version', 'name', 'version'),
    )


class AuditLog(Base):
    """Модель аудита"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Кто и что сделал
    user_id = Column(String(255))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(String(255))
    
    # Детали
    old_values = Column(JSON)
    new_values = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    # Временная метка
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Индексы
    __table_args__ = (
        Index('idx_audit_user', 'user_id', 'created_at'),
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
    )
