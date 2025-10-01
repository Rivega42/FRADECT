# 🏗️ FRADECT Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
├─────────────────────────────────────────────────────────────────┤
│  Web Dashboard  │  Mobile App  │  API Clients  │  Webhooks     │
└────────┬────────────────┬──────────────┬──────────────┬─────────┘
         │                │              │              │
         └────────────────┴──────────────┴──────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API GATEWAY                             │
│  (FastAPI + Kong/Nginx)                                         │
│  • Authentication (JWT)                                         │
│  • Rate limiting                                                │
│  • Request validation                                           │
│  • Load balancing                                               │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  E-Commerce  │  │  Financial   │  │   Project    │         │
│  │   Service    │  │   Service    │  │   Service    │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                    │
│                            ▼                                    │
│         ┌──────────────────────────────────────┐               │
│         │      CORE RISK ENGINE                │               │
│         │  • Feature extraction                │               │
│         │  • ML model inference                │               │
│         │  • Rule engine                       │               │
│         │  • Risk scoring                      │               │
│         └──────────────────────────────────────┘               │
│                            │                                    │
└────────────────────────────┼────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Feature    │   │     ML       │   │    Rule      │
│    Store     │   │   Models     │   │   Engine     │
│   (Feast)    │   │  (MLflow)    │   │  (Drools)    │
└──────────────┘   └──────────────┘   └──────────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  PostgreSQL  │  │    Redis     │  │Elasticsearch │         │
│  │ (Transact.)  │  │   (Cache)    │  │  (Search)    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  TimescaleDB │  │  S3/MinIO    │  │  Clickhouse  │         │
│  │ (Time-series)│  │   (Blob)     │  │  (Analytics) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL INTEGRATIONS                        │
├─────────────────────────────────────────────────────────────────┤
│  • Payment Gateways (CloudPayments, etc.)                       │
│  • CMS Platforms (Insales, Tilda, Shopify)                      │
│  • External Data (ЕГРЮЛ, ФССП, Контур.Фокус)                    │
│  • Device Fingerprinting (FingerprintJS)                        │
│  • Email/SMS (SendGrid, Twilio)                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Core Risk Engine

### Request Flow

```python
# 1. Request arrives
request = {
    "module": "ecommerce",
    "action": "score_transaction",
    "data": {...}
}

# 2. Feature extraction
features = feature_extractor.extract(
    request.data,
    include_historical=True,
    include_external=True
)

# 3. Parallel scoring
results = await asyncio.gather(
    ml_scorer.predict(features),
    rule_engine.evaluate(features),
    external_data_enrichment(features)
)

# 4. Combine scores
final_score = score_combiner.combine(
    ml_score=results[0],
    rule_score=results[1],
    external_signals=results[2]
)

# 5. Decision
decision = decision_maker.decide(
    score=final_score,
    threshold_config=config,
    business_context=request.context
)

# 6. Return (< 300ms)
return {
    "score": final_score,
    "decision": decision,
    "factors": [...],
    "request_id": uuid
}
```

### Feature Store Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FEATURE STORE (Feast)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ONLINE STORE (Redis)           OFFLINE STORE (S3 + Parquet)   │
│  • Real-time serving            • Training data                 │
│  • Low latency (<10ms)          • Historical features           │
│  • Recent features (7d)         • Feature backfills             │
│                                                                 │
│  Feature Groups:                                                │
│  ├─ customer_features                                           │
│  │  ├─ total_orders                                             │
│  │  ├─ avg_order_value                                          │
│  │  ├─ return_rate                                              │
│  │  └─ fraud_history                                            │
│  │                                                              │
│  ├─ transaction_features                                        │
│  │  ├─ amount                                                   │
│  │  ├─ currency                                                 │
│  │  ├─ payment_method                                           │
│  │  └─ device_fingerprint                                       │
│  │                                                              │
│  └─ derived_features                                            │
│     ├─ velocity_1h (orders last hour)                           │
│     ├─ velocity_24h                                             │
│     └─ geolocation_risk_score                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### ML Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        ML PIPELINE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. DATA INGESTION                                              │
│     ├─ Stream: Kafka → Feature Store                            │
│     └─ Batch: S3 → Feature Store                                │
│                                                                 │
│  2. FEATURE ENGINEERING                                         │
│     ├─ Python feature functions                                 │
│     ├─ Versioned in Git                                         │
│     └─ Deployed to Feature Store                                │
│                                                                 │
│  3. MODEL TRAINING                                              │
│     ├─ Scheduled (weekly) + on-demand                           │
│     ├─ Cross-validation                                         │
│     ├─ Hyperparameter tuning (Optuna)                           │
│     └─ Model registry (MLflow)                                  │
│                                                                 │
│  4. MODEL EVALUATION                                            │
│     ├─ Precision, Recall, F1                                    │
│     ├─ Business metrics ($ saved)                               │
│     ├─ Fairness checks                                          │
│     └─ Production A/B testing                                   │
│                                                                 │
│  5. MODEL DEPLOYMENT                                            │
│     ├─ Canary deployment                                        │
│     ├─ Shadow mode testing                                      │
│     └─ Blue-green rollout                                       │
│                                                                 │
│  6. MONITORING                                                  │
│     ├─ Data drift (Evidently)                                   │
│     ├─ Model drift                                              │
│     ├─ Performance metrics                                      │
│     └─ Alerts (Prometheus + PagerDuty)                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Models

### PostgreSQL Schema

```sql
-- Customers
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

-- Transactions
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

-- Risk Decisions
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

-- Projects
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

## API Design

### REST API

```python
# Score Transaction
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

Response:
{
  "score": 720,
  "decision": "REVIEW",
  "factors": [...],
  "request_id": "req_xyz",
  "processing_time_ms": 245
}

# Get Customer Risk Profile
GET /api/v1/customers/{customer_id}/risk-profile

Response:
{
  "customer_id": "cust_123",
  "ecommerce_risk": {...},
  "financial_risk": {...},
  "project_risk": {...},
  "overall_risk": "MEDIUM",
  "recommendations": [...]
}

# Batch Scoring
POST /api/v1/batch/score
{
  "items": [
    {"type": "transaction", "data": {...}},
    {"type": "transaction", "data": {...}}
  ]
}

Response:
{
  "job_id": "job_abc",
  "status": "PROCESSING",
  "estimated_completion": "2025-10-01T10:35:00Z"
}

GET /api/v1/batch/jobs/{job_id}
```

### Webhooks

```python
# Client registers webhook
POST /api/v1/webhooks
{
  "url": "https://client.com/webhooks/fradect",
  "events": ["risk.decision.created", "risk.decision.updated"],
  "secret": "whsec_..."
}

# FRADECT sends webhook
POST https://client.com/webhooks/fradect
Headers:
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

## Deployment

### Kubernetes

```yaml
# Deployment
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

# Horizontal Pod Autoscaler
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

### CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          pytest tests/ --cov=fradect
          
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: |
          docker build -t fradect/api:${{ github.sha }} .
          
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/fradect-api \
            api=fradect/api:${{ github.sha }}
          kubectl rollout status deployment/fradect-api
```

## Monitoring

### Metrics (Prometheus)

```python
# Application metrics
fradect_requests_total{module="ecommerce", decision="approve"}
fradect_requests_duration_seconds{module="ecommerce"}
fradect_model_predictions_total{model="fraud_v1.2", outcome="confirmed_fraud"}
fradect_feature_extraction_duration_seconds
fradect_false_positive_rate{module="ecommerce"}

# Business metrics
fradect_fraud_prevented_amount_total
fradect_customer_lifetime_value_protected
```

### Dashboards (Grafana)

```
Dashboard: System Health
├─ API Latency (p50, p95, p99)
├─ Throughput (requests/sec)
├─ Error Rate
├─ Database connections
└─ Cache hit rate

Dashboard: ML Performance
├─ Model accuracy over time
├─ Data drift score
├─ Feature importance drift
└─ Prediction distribution

Dashboard: Business Impact
├─ Fraud prevented ($)
├─ False positive rate
├─ Customer satisfaction (approval rate)
└─ ROI per customer
```

## Security

### Authentication & Authorization

```python
# JWT-based auth
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

# API key for server-to-server
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

### Data Privacy

```python
# PII encryption at rest
encrypted_email = encrypt(email, key=kms_key)

# PII masking in logs
logger.info(f"Processing transaction for {mask_email(email)}")
# Output: "Processing transaction for u***@example.com"

# GDPR compliance
# Right to be forgotten
DELETE /api/v1/customers/{customer_id}
# Pseudonymization for analytics
analytics_db.customer_id = hash(real_customer_id)
```

---

**Next:** See [API.md](API.md) for complete API reference.