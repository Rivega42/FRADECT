# 🏗️ Архитектура FRADECT

## Обзор системы

```
┌─────────────────────────────────────────────────────────────────┐
│                      КЛИЕНТСКИЙ УРОВЕНЬ                         │
├─────────────────────────────────────────────────────────────────┤
│  Веб-панель  │  Мобильное приложение  │  API-клиенты  │  Вебхуки│
└────────┬────────────────┬──────────────┬──────────────┬─────────┘
         │                │              │              │
         └────────────────┴──────────────┴──────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API ШЛЮЗ                                │
│  (FastAPI + Kong/Nginx)                                         │
│  • Аутентификация (JWT)                                         │
│  • Ограничение скорости                                         │
│  • Валидация запросов                                           │
│  • Балансировка нагрузки                                        │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ПРИКЛАДНОЙ УРОВЕНЬ                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Электронная  │  │  Финансовый  │  │  Проектный   │         │
│  │  коммерция   │  │    сервис    │  │    сервис    │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                    │
│                            ▼                                    │
│         ┌──────────────────────────────────────┐               │
│         │   ОСНОВНОЙ МОДУЛЬ ОЦЕНКИ РИСКОВ      │               │
│         │  • Извлечение признаков              │               │
│         │  • Инференс ML моделей               │               │
│         │  • Движок правил                     │               │
│         │  • Оценка рисков                     │               │
│         └──────────────────────────────────────┘               │
│                            │                                    │
└────────────────────────────┼────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Хранилище   │   │      ML      │   │    Движок    │
│  признаков   │   │    Модели    │   │    правил    │
│   (Feast)    │   │   (MLflow)   │   │   (Drools)   │
└──────────────┘   └──────────────┘   └──────────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      УРОВЕНЬ ДАННЫХ                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  PostgreSQL  │  │    Redis     │  │Elasticsearch │         │
│  │ (Транзакции) │  │    (Кэш)     │  │   (Поиск)    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  TimescaleDB │  │  S3/MinIO    │  │  Clickhouse  │         │
│  │(Временн.ряды)│  │  (Хранилище) │  │ (Аналитика)  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ВНЕШНИЕ ИНТЕГРАЦИИ                           │
├─────────────────────────────────────────────────────────────────┤
│  • Платежные шлюзы (CloudPayments и др.)                        │
│  • CMS платформы (Insales, Tilda, Shopify)                      │
│  • Внешние данные (ЕГРЮЛ, ФССП, Контур.Фокус)                   │
│  • Отпечаток устройства (FingerprintJS)                         │
│  • Email/SMS (SendGrid, Twilio)                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Основной модуль оценки рисков

### Поток обработки запроса

```python
# 1. Поступление запроса
request = {
    "module": "ecommerce",
    "action": "score_transaction",
    "data": {...}
}

# 2. Извлечение признаков
features = feature_extractor.extract(
    request.data,
    include_historical=True,
    include_external=True
)

# 3. Параллельная оценка
results = await asyncio.gather(
    ml_scorer.predict(features),
    rule_engine.evaluate(features),
    external_data_enrichment(features)
)

# 4. Объединение оценок
final_score = score_combiner.combine(
    ml_score=results[0],
    rule_score=results[1],
    external_signals=results[2]
)

# 5. Принятие решения
decision = decision_maker.decide(
    score=final_score,
    threshold_config=config,
    business_context=request.context
)

# 6. Возврат результата (< 300мс)
return {
    "score": final_score,
    "decision": decision,
    "factors": [...],
    "request_id": uuid
}
```

### Архитектура хранилища признаков

```
┌─────────────────────────────────────────────────────────────────┐
│                   ХРАНИЛИЩЕ ПРИЗНАКОВ (Feast)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ОНЛАЙН ХРАНИЛИЩЕ (Redis)       ОФЛАЙН ХРАНИЛИЩЕ (S3 + Parquet)│
│  • Обслуживание в реальном      • Данные для обучения          │
│    времени                      • Исторические признаки        │
│  • Низкая задержка (<10мс)      • Заполнение признаков         │
│  • Недавние признаки (7д)                                      │
│                                                                 │
│  Группы признаков:                                              │
│  ├─ признаки_клиента                                            │
│  │  ├─ всего_заказов                                            │
│  │  ├─ средняя_стоимость_заказа                                 │
│  │  ├─ процент_возвратов                                        │
│  │  └─ история_мошенничества                                    │
│  │                                                              │
│  ├─ признаки_транзакции                                         │
│  │  ├─ сумма                                                    │
│  │  ├─ валюта                                                   │
│  │  ├─ способ_оплаты                                            │
│  │  └─ отпечаток_устройства                                     │
│  │                                                              │
│  └─ производные_признаки                                        │
│     ├─ скорость_1ч (заказы за последний час)                    │
│     ├─ скорость_24ч                                             │
│     └─ оценка_риска_геолокации                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### ML конвейер

```
┌─────────────────────────────────────────────────────────────────┐
│                        ML КОНВЕЙЕР                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. ЗАГРУЗКА ДАННЫХ                                             │
│     ├─ Поток: Kafka → Хранилище признаков                       │
│     └─ Пакетная: S3 → Хранилище признаков                       │
│                                                                 │
│  2. ИНЖЕНЕРИЯ ПРИЗНАКОВ                                         │
│     ├─ Python функции признаков                                 │
│     ├─ Версионирование в Git                                    │
│     └─ Развертывание в хранилище признаков                      │
│                                                                 │
│  3. ОБУЧЕНИЕ МОДЕЛЕЙ                                            │
│     ├─ По расписанию (еженедельно) + по требованию              │
│     ├─ Кросс-валидация                                          │
│     ├─ Настройка гиперпараметров (Optuna)                       │
│     └─ Реестр моделей (MLflow)                                  │
│                                                                 │
│  4. ОЦЕНКА МОДЕЛЕЙ                                              │
│     ├─ Точность, полнота, F1                                    │
│     ├─ Бизнес-метрики (сэкономлено ₽)                           │
│     ├─ Проверки справедливости                                  │
│     └─ A/B тестирование в продакшене                            │
│                                                                 │
│  5. РАЗВЕРТЫВАНИЕ МОДЕЛЕЙ                                       │
│     ├─ Канареечное развертывание                                │
│     ├─ Тестирование в теневом режиме                            │
│     └─ Сине-зеленое развертывание                               │
│                                                                 │
│  6. МОНИТОРИНГ                                                  │
│     ├─ Дрейф данных (Evidently)                                 │
│     ├─ Дрейф модели                                             │
│     ├─ Метрики производительности                               │
│     └─ Оповещения (Prometheus + PagerDuty)                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Модели данных

### Схема PostgreSQL

```sql
-- Клиенты
CREATE TABLE customers (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    risk_tier VARCHAR(20),
    fraud_score INT,
    metadata JSONB
);

-- Транзакции
CREATE TABLE transactions (
    id UUID PRIMARY KEY,
    customer_id UUID REFERENCES customers(id),
    amount DECIMAL(10,2),
    currency VARCHAR(3),
    status VARCHAR(20),
    risk_score INT,
    decision VARCHAR(20),
    created_at TIMESTAMP,
    metadata JSONB,
    INDEX idx_customer_created (customer_id, created_at),
    INDEX idx_status (status)
);

-- Решения по рискам
CREATE TABLE risk_decisions (
    id UUID PRIMARY KEY,
    entity_type VARCHAR(50),  -- transaction, customer, project
    entity_id UUID,
    score INT,
    decision VARCHAR(20),
    factors JSONB,
    model_version VARCHAR(50),
    created_at TIMESTAMP,
    outcome VARCHAR(20),  -- confirmed_fraud, false_positive, unknown
    outcome_updated_at TIMESTAMP
);

-- Проекты
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    client_id UUID,
    estimated_budget DECIMAL(12,2),
    actual_budget DECIMAL(12,2),
    estimated_duration_days INT,
    actual_duration_days INT,
    risk_score INT,
    status VARCHAR(20),
    created_at TIMESTAMP,
    metadata JSONB
);
```

## Проектирование API

### REST API

```python
# Оценка транзакции
POST /api/v1/ecommerce/score
{
  "transaction": {
    "amount": 15000,
    "currency": "RUB",
    "customer_id": "cust_123",
    "device": {...},
    "shipping_address": {...}
  },
  "options": {
    "include_factors": true,
    "async": false
  }
}

Ответ:
{
  "score": 720,
  "decision": "REVIEW",
  "factors": [...],
  "request_id": "req_xyz",
  "processing_time_ms": 245
}

# Получить профиль риска клиента
GET /api/v1/customers/{customer_id}/risk-profile

Ответ:
{
  "customer_id": "cust_123",
  "ecommerce_risk": {...},
  "financial_risk": {...},
  "project_risk": {...},
  "overall_risk": "MEDIUM",
  "recommendations": [...]
}

# Пакетная оценка
POST /api/v1/batch/score
{
  "items": [
    {"type": "transaction", "data": {...}},
    {"type": "transaction", "data": {...}}
  ]
}

Ответ:
{
  "job_id": "job_abc",
  "status": "PROCESSING",
  "estimated_completion": "2025-10-01T10:35:00Z"
}

GET /api/v1/batch/jobs/{job_id}
```

### Вебхуки

```python
# Клиент регистрирует вебхук
POST /api/v1/webhooks
{
  "url": "https://client.com/webhooks/fradect",
  "events": ["risk.decision.created", "risk.decision.updated"],
  "secret": "whsec_..."
}

# FRADECT отправляет вебхук
POST https://client.com/webhooks/fradect
Заголовки:
  X-Fradect-Signature: sha256=...
  X-Fradect-Event: risk.decision.created

{
  "event": "risk.decision.created",
  "data": {
    "decision_id": "dec_123",
    "entity_type": "transaction",
    "entity_id": "txn_456",
    "score": 720,
    "decision": "REVIEW"
  },
  "timestamp": "2025-10-01T10:30:00Z"
}
```

## Развертывание

### Kubernetes

```yaml
# Развертывание
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fradect-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fradect-api
  template:
    spec:
      containers:
      - name: api
        image: fradect/api:v1.2.3
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: fradect-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

# Горизонтальный автомасштаб подов
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: fradect-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: fradect-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### CI/CD конвейер

```yaml
# .github/workflows/deploy.yml
name: Развертывание

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Запуск тестов
        run: |
          pytest tests/ --cov=fradect
          
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Сборка Docker образа
        run: |
          docker build -t fradect/api:${{ github.sha }} .
          
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Развертывание в Kubernetes
        run: |
          kubectl set image deployment/fradect-api \
            api=fradect/api:${{ github.sha }}
          kubectl rollout status deployment/fradect-api
```

## Мониторинг

### Метрики (Prometheus)

```python
# Метрики приложения
fradect_requests_total{module="ecommerce", decision="approve"}
fradect_requests_duration_seconds{module="ecommerce"}
fradect_model_predictions_total{model="fraud_v1.2", outcome="confirmed_fraud"}
fradect_feature_extraction_duration_seconds
fradect_false_positive_rate{module="ecommerce"}

# Бизнес-метрики
fradect_fraud_prevented_amount_total
fradect_customer_lifetime_value_protected
```

### Дашборды (Grafana)

```
Дашборд: Здоровье системы
├─ Задержка API (p50, p95, p99)
├─ Пропускная способность (запросов/сек)
├─ Процент ошибок
├─ Подключения к БД
└─ Процент попаданий в кэш

Дашборд: Производительность ML
├─ Точность модели со временем
├─ Оценка дрейфа данных
├─ Дрейф важности признаков
└─ Распределение предсказаний

Дашборд: Бизнес-влияние
├─ Предотвращено мошенничества (₽)
├─ Процент ложных срабатываний
├─ Удовлетворенность клиентов (процент одобрений)
└─ ROI на клиента
```

## Безопасность

### Аутентификация и авторизация

```python
# Аутентификация на основе JWT
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

# API ключ для сервер-сервер
headers = {
    "X-API-Key": "fdk_live_..."
}

# RBAC
user.roles = ["admin", "analyst"]

permissions = {
    "admin": ["*"],
    "analyst": ["read:transactions", "read:customers"],
    "api_user": ["write:transactions", "read:risk_decisions"]
}
```

### Конфиденциальность данных

```python
# Шифрование PII в состоянии покоя
encrypted_email = encrypt(email, key=kms_key)

# Маскирование PII в логах
logger.info(f"Обработка транзакции для {mask_email(email)}")
# Вывод: "Обработка транзакции для u***@example.com"

# Соответствие GDPR
# Право на забвение
DELETE /api/v1/customers/{customer_id}
# Псевдонимизация для аналитики
analytics_db.customer_id = hash(real_customer_id)
```

---

**Далее:** См. [API.md](API.md) для полной справки по API.
