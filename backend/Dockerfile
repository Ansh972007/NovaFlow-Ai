FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc default-libmysqlclient-dev libpq-dev curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 novaflow \
    && useradd --system --uid 1001 -g novaflow novaflow

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

RUN mkdir -p /app/data/uploads /app/data/keys /app/components \
    && chown -R novaflow:novaflow /app/data /app/components

ENV PYTHONUNBUFFERED=1
ENV NOVAFLOW_HOST=0.0.0.0
ENV NOVAFLOW_PORT=3001
ENV NOVAFLOW_ENV=development
ENV DATA_DIR=/app/data
ENV COMPONENT_DIR=/app/components

# Feature flags (override in docker-compose / .env.docker)
ENV UNIVERSAL_CHAT_ENABLED=1
ENV ENABLE_DYNAMIC_COMPONENT_CREATION=1
ENV ENABLE_API_REQUIREMENT_GATHERING=1
ENV ENABLE_LLM_GRAPH_COMPOSE=1
ENV ENABLE_CONVERSATION_API_KEYS=1

# Dev-friendly defaults — production compose sets STRICT_SECURITY_MODE=1 etc.
ENV STRICT_SECURITY_MODE=0
ENV ENFORCE_GMAIL_ONLY=0
ENV REQUIRE_USER_API_KEYS=0
ENV USER_API_KEY_REQUIRED=0
ENV ALLOW_PASSWORD_LOGIN=1

USER novaflow
EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3001/health', timeout=3)"

CMD ["python", "-m", "app.main"]
