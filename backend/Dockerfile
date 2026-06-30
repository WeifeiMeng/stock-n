ARG BASE_REGISTRY=docker.io

FROM ${BASE_REGISTRY}/library/python:3.13-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev -i https://pypi.tuna.tsinghua.edu.cn/simple

FROM ${BASE_REGISTRY}/library/python:3.13-slim

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos "" --home /app appuser

COPY --from=builder /app/.venv ./.venv
COPY main.py ./
COPY src/ ./src/
COPY scripts/ ./scripts/

RUN mkdir -p /app/log && chown -R appuser:appuser /app

EXPOSE 8000

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
