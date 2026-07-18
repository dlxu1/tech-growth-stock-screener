FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    TECH_GROWTH_SCREENER_CACHE=/app/.cache \
    TECH_GROWTH_DB=/app/.cache/stock_data.sqlite

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/.cache/reports

EXPOSE 5001

CMD ["python", "scripts/run.py", "dashboard-server", "--source", "cache", "--host", "0.0.0.0", "--port", "5001"]
