FROM python:3.11-slim

ARG APT_MIRROR=
ARG PIP_INDEX_URL=

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    TECH_GROWTH_SCREENER_CACHE=/app/.cache \
    TECH_GROWTH_DB=/app/.cache/stock_data.sqlite

WORKDIR /app

RUN if [ -n "$APT_MIRROR" ]; then \
        sed -i "s|http://deb.debian.org/debian|$APT_MIRROR|g; s|http://deb.debian.org/debian-security|$APT_MIRROR-security|g" /etc/apt/sources.list.d/debian.sources; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN if [ -n "$PIP_INDEX_URL" ]; then \
        python -m pip config set global.index-url "$PIP_INDEX_URL"; \
    fi \
    && python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/.cache/reports

EXPOSE 5001

CMD ["python", "scripts/run.py", "dashboard-server", "--source", "cache", "--host", "0.0.0.0", "--port", "5001"]
