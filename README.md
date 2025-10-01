# 🛡️ FRADECT

**Innovative AI-Powered Risk Management & Fraud Detection Platform**

![Status](https://img.shields.io/badge/status-mvp-yellow)
![License](https://img.shields.io/badge/license-proprietary-red)
![Python](https://img.shields.io/badge/python-3.9+-blue)

**English** | [Русский](README_RU.md)

## 🎯 Mission

FRADECT transforms risk management from reactive "fighting fires" to proactive "predicting and preventing" losses. We built a unified platform that answers one question: **"What will we lose if we don't act now?"**

## 🧠 Philosophy: Risk-First Thinking

Inspired by Larry Fink's BlackRock principle after his $100M loss:
> "Ask 'What can we lose?' before asking 'What can we earn?'"

FRADECT applies this to:
- E-commerce fraud
- Accounts receivable
- Project risks
- Contractor evaluation
- Customer risks

**Read more:** [Philosophy Document](docs/PHILOSOPHY.md)

## 🏗️ Platform Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    FRADECT CORE ENGINE                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ML Pipeline  │  │ Rule Engine  │  │ Risk Scoring │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────────────────────────────────────────┘
                            │
        ┌──────────────────────┼──────────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   E-COMMERCE │    │  FINANCIAL   │    │   PROJECT    │
│    MODULE    │    │    MODULE    │    │   MODULE     │
│              │    │              │    │              │
│ • Payment    │    │ • Debtor     │    │ • Kickoff    │
│   Fraud      │    │   Risk       │    │   Risk       │
│ • Return     │    │ • Credit     │    │ • Contractor │
│   Abuse      │    │   Limits     │    │   Scoring    │
│ • Promo      │    │ • Collection │    │ • Customer   │
│   Gaming     │    │   Priority   │    │   Scoring    │
└──────────────┘    └──────────────┘    └──────────────┘
```

## 📦 Modules

### 1️⃣ E-Commerce Risk Module
**Problem:** Online stores lose 1.5-3.5% revenue to fraud

**Solutions:**
- **Payment Fraud Detection**: Real-time transaction scoring
- **Return Abuse Prevention**: Pattern detection for serial returners
- **Promo Code Gaming**: Multi-account abuse detection

**Integration:**
- API layer between CMS (Insales, Tilda) and Payment Gateway (CloudPayments)
- Decision in <300ms
- Actions: approve/review/decline

**Learn more:** [Modules Documentation](docs/MODULES.md)

### 2️⃣ Financial Risk Module
**Problem:** Companies turn into involuntary banks with huge accounts receivable

**Solutions:**
- **Debtor Risk Scoring**: Predict payment delays before extending credit
- **Dynamic Credit Limits**: Adjust limits based on behavior
- **Collection Prioritization**: Focus on recoverable debts

**Output:**
- Risk tier: A-F
- Recommended credit limit
- Probability of default: 0-100%
- Next payment prediction

### 3️⃣ Project Risk Module
**Problem:** 70% of projects exceed budget/timeline

**Solutions:**
- **Project Kickoff Risk Assessment**: Budget realism check, timeline feasibility
- **Contractor Scoring**: Pre-contract risk assessment
- **Customer Project Risk**: Client payment probability, scope creep likelihood

## 🎮 Competitive Advantages

**Russian Market Gap:**
- ✅ Payment fraud: Group-IB, QIWI (expensive, 1M+ ₽/year)
- ✅ Debtor risk: FIS Collection, AFS (enterprise only)
- ✅ Project risk: ТАМАРА (complex, 6-12 months implementation)
- ❌ **INTEGRATED SOLUTION: None**

**FRADECT Advantage:**
```
┌────────────────────────────────────────────────────────────┐
│  E-commerce + Financial + Project = 3-in-1 Platform       │
│                                                            │
│  • 10x cheaper than enterprise solutions                   │
│  • 10x faster implementation (weeks vs months)             │
│  • AI-powered (competitors use rule-based systems)         │
│  • Unified risk view across business                       │
└────────────────────────────────────────────────────────────┘
```

## 🎯 Target Market

### Primary (MVP):
- **SMB E-commerce**: 10-500M ₽ revenue
  - Fashion, electronics, home goods
  - Current fraud losses: 1.5-3.5% revenue

### Secondary:
- **B2B Companies**: with payment terms (Distribution, manufacturing)
- **Project-Based Businesses**: Construction, IT development, consulting

## 💰 Business Model

### E-commerce Module:
```
Option 1: Transaction-based
├─ 0.1-0.3% per transaction processed
├─ Or: 10-30% of fraud prevented
└─ Pricing tier by volume

Option 2: SaaS
├─ Basic: $99/mo (up to 1K transactions)
├─ Pro: $299/mo (up to 10K transactions)
└─ Enterprise: Custom
```

## 🚀 Roadmap

### Phase 1: MVP (Months 1-3) ✅
- [x] E-commerce fraud module
- [x] Basic ML pipeline
- [x] API infrastructure
- [x] Demo dashboard

### Phase 2: Financial Module (Months 4-6)
- [ ] Debtor risk scoring
- [ ] Credit limit recommendations
- [ ] Collection prioritization

### Phase 3: Project Module (Months 7-9)
- [ ] Project kickoff assessment
- [ ] Contractor scoring
- [ ] Customer risk evaluation

## 🛠️ Technology Stack

### Core:
```python
├─ Language: Python 3.9+
├─ ML: scikit-learn, XGBoost, LightGBM
├─ Deep Learning: TensorFlow/PyTorch
├─ Feature Store: Feast
└─ MLOps: MLflow
```

### API & Backend:
```
├─ Framework: FastAPI
├─ Database: PostgreSQL
├─ Cache: Redis
├─ Queue: Celery + RabbitMQ
└─ Search: Elasticsearch
```

**Full tech details:** [Architecture Document](docs/ARCHITECTURE.md)

## 📊 Key Metrics

### Product Metrics:
```
├─ Precision: >90% (minimize false positives)
├─ Recall: >85% (catch most fraud)
├─ Response Time: <300ms (real-time)
├─ Uptime: >99.9%
└─ Model Drift: Monitor weekly
```

### Business Metrics:
```
├─ Customer fraud reduction: 40-60%
├─ False positive rate: <5%
├─ ROI for customer: 5-10x
├─ Implementation time: <2 weeks
└─ Customer retention: >90%
```

## 🧪 Pilot Strategy

```
1. Identify pilot partner
2. Free 3-4 month pilot
3. Select 1-2 modules
4. Define success metrics
5. Weekly check-ins
6. Results presentation
7. Commercial terms negotiation
```

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/Rivega42/FRADECT.git
cd FRADECT

# Run with Docker Compose
docker-compose up -d

# Access API
curl http://localhost:8000/

# Access docs
open http://localhost:8000/docs
```

## 📚 Documentation

- [📖 Philosophy & Risk-First Thinking](docs/PHILOSOPHY.md)
- [🏗️ Technical Architecture](docs/ARCHITECTURE.md)
- [📦 Modules Deep Dive](docs/MODULES.md)
- [🇷🇺 Russian README](README_RU.md)

## 📞 Contact

For partnerships, pilots, or investment inquiries - please reach out via GitHub issues.

## 📄 License

Proprietary. All rights reserved.

---

**Built with ❤️ to prevent losses and protect business**
