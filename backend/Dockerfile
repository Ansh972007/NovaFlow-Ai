FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN mkdir -p /app/data/uploads

ENV PYTHONUNBUFFERED=1
ENV NOVAFLOW_HOST=0.0.0.0
ENV NOVAFLOW_PORT=3001

EXPOSE 3001

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001", "--workers", "2"]
