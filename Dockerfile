# Multi-stage build for efficient and secure containerization
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock .
RUN pip install --no-cache-dir --prefix=/install -r requirements.lock

# Final production stage
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:${PATH}" \
    PYTHONPATH="/install/lib/python3.11/site-packages:/app:${PYTHONPATH}" \
    HOME="/app" \
    CHECKPOINT_DB_PATH=state/checkpoints.db \
    TICKETS_DB_PATH=state/tickets.db

# Create non-root system group and user
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

# Copy installed packages from builder
COPY --from=builder /install /install

# Copy project files
COPY src ./src
COPY data ./data
COPY README.md .

# Create state directory owned by appuser for persistent databases
RUN mkdir -p /app/state && chown -R appuser:appgroup /app/state

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
