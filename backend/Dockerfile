FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc default-libmysqlclient-dev curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 novaflow \
    && useradd --system --uid 1001 -g novaflow novaflow

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

RUN mkdir -p /app/data/uploads /app/data/keys /app/components \
    && chown -R novaflow:novaflow /app/data /app/components

ENV PYTHONUNBUFFERED=1
ENV NOVAFLOW_HOST=0.0.0.0
ENV NOVAFLOW_PORT=3001
# STRICT SECURITY: Production-grade security always enforced
ENV NOVAFLOW_ENV=production
ENV NOVAFLOW_ADMIN_PASSWORD=NovaFlowSecureAdminPassword2024!
# STRICT: Security mode cannot be bypassed
ENV STRICT_SECURITY_MODE=1
ENV ENFORCE_GMAIL_ONLY=1
ENV REQUIRE_USER_API_KEYS=1

# Universal AI Chat System Configuration
ENV UNIVERSAL_CHAT_ENABLED=1
ENV COMPONENT_DIR=/app/components
ENV ENABLE_DYNAMIC_COMPONENT_CREATION=1
ENV ENABLE_API_REQUIREMENT_GATHERING=1

# User Role Management & API Key System
ENV GMAIL_ONLY_AUTH=1
ENV USER_API_KEY_REQUIRED=1
ENV ENABLE_CONVERSATION_API_KEYS=1
ENV DEFAULT_USER_ROLE=admin
ENV DEFAULT_USER_PROVIDER=openrouter
ENV DEFAULT_USER_MODEL=openai/gpt-4o-mini

# OpenRouter API Configuration
ENV OPENAI_API_KEY=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
ENV OPENAI_BASE_URL=https://openrouter.ai/api/v1
ENV OPENAI_MODEL=openai/gpt-4o-mini

USER novaflow
EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3001/health', timeout=3)"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001", "--workers", "1"]
