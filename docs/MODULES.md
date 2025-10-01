# 📦 FRADECT Modules Deep Dive

## Overview

FRADECT consists of three core modules, each addressing a specific risk domain:

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRADECT PLATFORM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐       │
│  │  E-COMMERCE  │   │  FINANCIAL   │   │   PROJECT    │       │
│  │    RISK      │   │    RISK      │   │    RISK      │       │
│  └──────────────┘   └──────────────┘   └──────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module 1: E-Commerce Risk

### Problem Statement

Online retailers lose **1.5-3.5% of revenue** to various forms of fraud:
- Payment fraud (stolen cards, account takeover)
- Return abuse (wardrobing, empty box returns)
- Promo code gaming (multi-account abuse, coupon farms)

For a store with 100M ₽ revenue, this means **1.5-3.5M ₽ annual losses**.

### Sub-Modules

#### 1.1 Payment Fraud Detection

**Input Data:**
```python
{
  "transaction_id": "txn_123456",
  "amount": 15000,
  "currency": "RUB",
  "customer": {
    "id": "cust_789",
    "email": "user@example.com",
    "phone": "+79161234567",
    "registration_date": "2024-01-15",
    "total_orders": 3
  },
  "device": {
    "fingerprint": "fp_abc123",
    "ip": "93.170.123.45",
    "user_agent": "...",
    "timezone": "Europe/Moscow"
  },
  "shipping_address": {...},
  "billing_address": {...},
  "timestamp": "2025-10-01T10:30:00Z"
}
```

**Risk Factors Analyzed:**
```
├─ Device Fingerprint
│  ├─ Known fraudulent device?
│  ├─ Multiple accounts from this device?
│  └─ Device-location mismatch?
│
├─ Behavioral Signals
│  ├─ Time on site before purchase
│  ├─ Navigation pattern
│  ├─ Copy-paste in forms (suggests credential stuffing)
│  └─ Multiple failed payment attempts
│
├─ Velocity Checks
│  ├─ Multiple orders in short time?
│  ├─ Same card on multiple accounts?
│  └─ Rapid-fire checkout (bot behavior)?
│
├─ Network Analysis
│  ├─ Email domain reputation
│  ├─ IP geolocation vs shipping
│  ├─ VPN/proxy usage
│  └─ Device fingerprint clusters
│
└─ Historical Patterns
   ├─ Customer payment history
   ├─ Similar transactions outcomes
   └─ Address history (delivery success)
```

**Output:**
```python
{
  "risk_score": 720,  # 0-1000 scale
  "risk_tier": "HIGH",  # LOW/MEDIUM/HIGH/CRITICAL
  "recommendation": "REVIEW",  # APPROVE/REVIEW/DECLINE
  "confidence": 0.87,
  "expected_loss": 12750,  # 85% probability * 15000 amount
  "risk_factors": [
    {
      "factor": "device_fingerprint_blacklist",
      "impact": -180,
      "description": "Device linked to 3 previous chargebacks"
    },
    {
      "factor": "velocity_check_failed",
      "impact": -120,
      "description": "4th order in 2 hours"
    },
    {
      "factor": "geolocation_mismatch",
      "impact": -95,
      "description": "IP in Moscow, shipping to Vladivostok"
    }
  ],
  "suggested_actions": [
    "Request additional verification (ID photo)",
    "Contact customer via phone",
    "Ship with signature required"
  ]
}
```

**Integration Flow:**
```
Customer checkout
     ↓
CMS (Insales/Tilda)
     ↓
FRADECT API (< 300ms response)
     ↓
┌─────────────────┐
│ If APPROVE:     │ → Payment Gateway → Bank
│ If REVIEW:      │ → Manual review queue
│ If DECLINE:     │ → Show friendly error
└─────────────────┘
```

#### 1.2 Return Abuse Detection

**Problem:** Serial returners, wardrobing (wear once & return), empty box scams.

**Input Data:**
```python
{
  "customer_id": "cust_789",
  "order_history": [
    {"order_id": "ord_001", "returned": true, "reason": "didn't fit"},
    {"order_id": "ord_002", "returned": true, "reason": "wrong color"},
    {"order_id": "ord_003", "returned": false},
    {"order_id": "ord_004", "returned": true, "reason": "quality issue"}
  ],
  "return_request": {
    "order_id": "ord_005",
    "items": [{...}],
    "reason": "doesn't fit",
    "timestamp": "2025-10-01T15:00:00Z"
  }
}
```

**Risk Patterns:**
```
├─ Return Frequency
│  └─ >40% return rate (industry avg: 15-20%)
│
├─ Temporal Patterns
│  ├─ Returns after major events (wore to event?)
│  └─ Consistent return window (always day 29 of 30)
│
├─ Item-Specific
│  ├─ High-value items only
│  ├─ Seasonal items (dresses before wedding season)
│  └─ Tags removed vs intact
│
└─ Cross-Reference
   ├─ Social media posts (wearing returned item?)
   └─ Multiple accounts, same address
```

**Output:**
```python
{
  "abuse_score": 850,
  "classification": "SERIAL_RETURNER",
  "recommendation": "RESTRICT_RETURNS",
  "actions": [
    "Flag account for manual approval on future returns",
    "Charge 15% restocking fee",
    "Require photo proof of defect"
  ],
  "lifetime_value_at_risk": -2500  # Net negative customer
}
```

#### 1.3 Promo Code Gaming

**Problem:** Users create multiple accounts to abuse first-order discounts, referral programs.

**Detection Methods:**
```
├─ Device Fingerprinting
│  └─ Same device, multiple accounts
│
├─ Network Analysis
│  ├─ Email patterns (name+1@, name+2@)
│  ├─ Phone number clusters
│  └─ Address variations (Apt 1, Apt 1A, Apt #1)
│
├─ Behavioral
│  ├─ Accounts created in rapid sequence
│  ├─ Identical cart contents
│  └─ Checkout within minutes of signup
│
└─ Social Graph
   └─ Referral chains (A→B→C→D, all same IP)
```

---

## Module 2: Financial Risk

### Problem Statement

Companies with payment terms (B2B, distributors) face:
- **20-40% of revenue locked in accounts receivable**
- **5-15% becomes bad debt** (never collected)
- Inefficient collection efforts (chasing wrong debtors)

### Sub-Modules

#### 2.1 Debtor Risk Scoring

**Before extending credit**, predict: Will this client pay on time?

**Input Data:**
```python
{
  "client_id": "client_456",
  "invoice_history": [
    {
      "invoice_id": "inv_001",
      "amount": 50000,
      "due_date": "2025-08-01",
      "paid_date": "2025-08-15",  # 14 days late
      "delay_days": 14
    },
    # ... more history
  ],
  "company_info": {
    "industry": "retail",
    "size": "10-50 employees",
    "years_in_business": 7,
    "public_filings": {...}  # if available
  },
  "external_data": {
    "fssp_records": false,  # no bailiff records
    "legal_cases": 0,
    "credit_bureau_score": null  # if available
  },
  "requested_credit": 100000,
  "payment_terms": "net_30"
}
```

**Feature Engineering:**
```python
features = [
    # Payment behavior
    payment_punctuality_rate,  # % on-time payments
    avg_delay_days,
    max_delay_days,
    payment_trend,  # improving/stable/worsening
    
    # Financial exposure
    current_outstanding_debt,
    credit_utilization,  # outstanding / limit
    
    # Temporal
    days_since_last_payment,
    payment_frequency,
    seasonal_patterns,
    
    # Business context
    industry_risk_factor,
    company_age,
    relationship_length,
    
    # External signals
    has_legal_issues,
    fssp_records,
    public_negative_news
]
```

**Model Output:**
```python
{
  "risk_score": 425,  # 0-1000, lower = better
  "risk_tier": "B",  # A-F scale
  "default_probability": 0.12,  # 12% chance of non-payment
  "recommended_credit_limit": 75000,  # less than requested
  "payment_terms": "net_15",  # tighten terms
  "required_prepayment": 0.25,  # 25% upfront
  
  "risk_factors": [
    {
      "factor": "payment_trend_worsening",
      "impact": "Last 3 invoices avg 18 days late vs 8 days prior"
    },
    {
      "factor": "high_credit_utilization",
      "impact": "Currently using 85% of existing limit"
    }
  ],
  
  "predicted_behavior": {
    "expected_payment_date": "2025-11-17",  # 17 days after due
    "confidence_interval": ["2025-11-10", "2025-11-25"]
  }
}
```

#### 2.2 Dynamic Credit Limits

**Automatically adjust limits** based on real-time behavior.

**Logic:**
```python
if payment_trend == "improving" and punctuality > 0.9:
    action = "increase_limit"
    new_limit = current_limit * 1.2
    
elif payment_trend == "worsening" or max_delay > 45:
    action = "decrease_limit"
    new_limit = current_limit * 0.7
    notify_account_manager = True
    
elif outstanding > (limit * 0.8):
    action = "block_new_orders"
    message = "Reduce outstanding to below 80% to resume"
```

#### 2.3 Collection Prioritization

**Which debts to chase first?**

**Scoring:**
```python
collection_priority_score = (
    debt_amount * recoverability_prob * urgency_factor
) / collection_cost_estimate

where:
  recoverability_prob = f(
      client_financial_health,
      relationship_quality,
      legal_collectability
  )
  
  urgency_factor = f(
      days_overdue,
      debt_aging_category  # 0-30, 31-60, 61-90, 90+
  )
```

**Output:**
```python
[
  {
    "client": "Client A",
    "debt": 150000,
    "days_overdue": 45,
    "priority_score": 8.5,
    "recovery_prob": 0.75,
    "recommended_action": "Personal call from account manager",
    "expected_recovery": 112500
  },
  {
    "client": "Client B",
    "debt": 80000,
    "days_overdue": 120,
    "priority_score": 3.2,
    "recovery_prob": 0.20,
    "recommended_action": "Transfer to collection agency",
    "expected_recovery": 16000
  }
]
```

---

## Module 3: Project Risk

### Problem Statement

**70% of projects** exceed budget and/or timeline.

Common causes:
- Optimistic initial estimates
- Scope creep
- Wrong team/contractor
- Hidden dependencies
- Client payment delays

### Sub-Modules

#### 3.1 Project Kickoff Risk Assessment

**Before starting**, evaluate if project will succeed.

**Input:**
```python
{
  "project": {
    "name": "ERP System Integration",
    "description": "...",
    "estimated_budget": 2000000,
    "estimated_duration_days": 180,
    "scope": "...",
    "client": "..."
  },
  "team": [
    {"role": "PM", "experience_years": 3, "similar_projects": 2},
    {"role": "Dev", "experience_years": 5, "tech_stack_match": 0.8}
  ],
  "dependencies": [
    "Client provides API access by Week 2",
    "Third-party vendor integration"
  ]
}
```

**Analysis:**
```python
# Compare to historical similar projects
similar_projects = find_similar(
    scope=current.scope,
    budget_range=current.budget * [0.7, 1.3],
    industry=current.client.industry
)

historical_outcomes = [
    {"budget_overrun": 1.45, "timeline_overrun": 1.30},
    {"budget_overrun": 1.20, "timeline_overrun": 1.15},
    {"budget_overrun": 1.80, "timeline_overrun": 1.60},
    # ... 7 more
]

avg_budget_overrun = 1.48  # 48% over
avg_timeline_overrun = 1.35  # 35% over
success_rate = 0.30  # 30% delivered on-budget & on-time
```

**Output:**
```python
{
  "success_probability": 0.35,
  "predicted_final_budget": 2960000,  # +48%
  "predicted_final_timeline": 243,  # +35% days
  
  "risk_factors": [
    {
      "factor": "Team experience mismatch",
      "severity": "HIGH",
      "impact": "PM has only done 2 similar projects, avg is 5+",
      "mitigation": "Bring in senior PM as advisor"
    },
    {
      "factor": "External dependencies",
      "severity": "MEDIUM",
      "impact": "Reliance on client API access historically delays 30% of projects",
      "mitigation": "Build mockup environment, don't wait for client"
    },
    {
      "factor": "Scope ambiguity",
      "severity": "HIGH",
      "impact": "Unclear requirements lead to 50%+ scope creep",
      "mitigation": "Conduct 2-week discovery phase before committing to fixed price"
    }
  ],
  
  "recommendation": "NEGOTIATE",
  "suggested_changes": {
    "budget": 3000000,  # Add buffer
    "timeline": 240,  # Add buffer
    "payment_terms": "40% upfront, 30% at milestone 1, 30% at delivery",
    "scope": "Fixed scope with change order process"
  }
}
```

#### 3.2 Contractor Scoring

**Before signing contract**, assess if contractor will deliver.

**Risk Factors:**
```
├─ Financial Health
│  ├─ Recent financial filings
│  ├─ Payment to suppliers (delayed?)
│  └─ Outstanding legal cases
│
├─ Team Stability
│  ├─ Employee turnover rate
│  ├─ Key personnel departures
│  └─ Hiring spree (overcommitted?)
│
├─ Portfolio Fit
│  ├─ Similar projects delivered
│  ├─ Technical capability match
│  └─ Industry experience
│
├─ Delivery Track Record
│  ├─ On-time delivery %
│  ├─ Budget adherence
│  └─ Client satisfaction scores
│
└─ Capacity
   ├─ Current project load
   ├─ Available resources
   └─ Subcontractor reliance
```

#### 3.3 Customer Project Risk

**Will the CLIENT be a problem?**

**Risk Patterns:**
```
├─ Payment History
│  └─ Late payments on past projects?
│
├─ Decision-Making
│  ├─ Slow approval processes
│  └─ Frequent leadership changes
│
├─ Scope Management
│  ├─ History of scope creep
│  └─ Unclear requirements
│
└─ Communication
   └─ Responsiveness, clarity
```

---

## Cross-Module Synergies

### Unified Risk View

```python
# Customer 360° risk profile
customer_risk = {
    "ecommerce": {
        "fraud_score": 250,  # Low risk
        "return_abuse_score": 120,  # Low risk
    },
    "financial": {
        "payment_risk": 680,  # Medium-high risk
        "current_ar": 50000,
    },
    "project": {
        "scope_creep_prob": 0.65,  # High risk
        "payment_delay_prob": 0.40
    },
    
    "overall_risk": "MEDIUM-HIGH",
    "recommended_strategy": "Accept orders with prepayment only"
}
```

### Shared Learning

Insights from one module inform others:
- Payment delays in AR → flag as risky project client
- Return abuse in e-commerce → tighten project payment terms
- Project scope creep → reduce credit limit

---

## Implementation Priority

### Phase 1 (MVP): E-Commerce Module
**Why:** Fastest ROI, clear metrics, easier data access

### Phase 2: Financial Module
**Why:** Builds on payment data, high business impact

### Phase 3: Project Module
**Why:** More complex, requires historical project data

---

**Next:** See [ARCHITECTURE.md](ARCHITECTURE.md) for technical implementation details.