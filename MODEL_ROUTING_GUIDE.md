# Model Routing & AB Splitting Guide

NovaFlow includes a model routing engine that dynamically matches, tests, and shifts traffic between different AI engines.

---

## 1. AB Model Routes
Navigate to the **AI Providers** settings hub. Here, you can configure model variations for AB testing:
- **Base Model**: The default target model (e.g., `gpt-4o-mini`).
- **Variant Model**: The test candidate (e.g., `gemini-1.5-flash`).
- **Variant Traffic Percentage ($pct$)**: The likelihood (from 0 to 100) that a given user interaction is routed to the variant model instead of the base model.

---

## 2. Dynamic Selection Rules
During chat executions, NovaFlow automatically evaluates routes:
```python
# Evaluates traffic split weights
use_variant = random.randint(1, 100) <= pct
picked_model = variant_model if use_variant else base_model
```
Use this configuration to benchmark model performance, test local models against commercial APIs, or run cost-efficiency experiments in production.
