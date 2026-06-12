FROM python:3.11-slim-bookworm as builder

# Install poetry
RUN pip install poetry==1.7.1

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

# Copy internal packages
COPY packages/eaioc-core /packages/eaioc-core
COPY packages/eaioc-database /packages/eaioc-database

# Copy edge-manager
COPY services/edge-manager/pyproject.toml services/edge-manager/poetry.lock* ./services/edge-manager/
WORKDIR /app/services/edge-manager

# Install dependencies
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

# Runtime Stage
FROM python:3.11-slim-bookworm as runtime

ENV VIRTUAL_ENV=/app/services/edge-manager/.venv \
    PATH="/app/services/edge-manager/.venv/bin:$PATH"

WORKDIR /app

# Copy dependencies
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

# Copy code
COPY packages/eaioc-core /packages/eaioc-core
COPY packages/eaioc-database /packages/eaioc-database
COPY services/edge-manager /app/services/edge-manager

WORKDIR /app/services/edge-manager

# Run as non-root
RUN useradd -m -U appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8007

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8007"]
