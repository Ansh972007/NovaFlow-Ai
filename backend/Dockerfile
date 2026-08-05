FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 novaflow \
    && useradd --system --uid 1001 -g novaflow novaflow

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

RUN mkdir -p /app/data/uploads /app/data/keys \
    && chown -R novaflow:novaflow /app/data

ENV PYTHONUNBUFFERED=1
ENV NOVAFLOW_HOST=0.0.0.0
ENV NOVAFLOW_PORT=3001
# Override to production in real deployments (compose/k8s).
ENV NOVAFLOW_ENV=development

USER novaflow
EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3001/health', timeout=3)"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001", "--workers", "1"]
