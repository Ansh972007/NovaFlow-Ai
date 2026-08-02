# NovaFlow Free Forever Architecture

This document describes the design philosophy and architecture of NovaFlow's free-forever, self-hosted, and provider-agnostic edition.

---

## 1. Product Philosophy
NovaFlow is an orchestration workspace, not an AI model reseller.
- **BYOK (Bring Your Own Key)**: Users connect directly to their own inference endpoints (cloud, enterprise private, or local offline).
- **No Markups**: The platform never sits in the middle of billing transactions or billing metrics.
- **Zero Subscriptions**: There are no pricing tiers, subscription paywalls, or features hidden behind licensing agreements.

---

## 2. Retention of Observability & Analytics Telemetry
While payment gateways, stripe webhooks, and billing components have been permanently purged, NovaFlow retains all **operational analytics** and **telemetry**:
- **Token Analytics**: Tracking prompt, completion, and total token usage to give users insight into their provider spending.
- **Performance Telemetry**: Measuring latency, request frequency, success/failure rates, and model errors.
- **Resource Statistics**: Monitoring execution metrics of KnowledgeOS databases, voice command pipelines, and AgentOS subprocess runs.

---

## 3. Deployment Topology
NovaFlow is fully containerized and runs locally or self-hosted in private enterprise clouds (AWS, GCP, Azure, or on-premise hardware) with zero dependencies on commercial SaaS control planes.
