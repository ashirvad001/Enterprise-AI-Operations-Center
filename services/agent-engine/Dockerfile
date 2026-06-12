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
COPY packages/eaioc-events /packages/eaioc-events

# Copy agent-engine
COPY services/agent-engine/pyproject.toml services/agent-engine/poetry.lock* ./services/agent-engine/
WORKDIR /app/services/agent-engine

# Install dependencies
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

# Runtime Stage
FROM python:3.11-slim-bookworm as runtime

ENV VIRTUAL_ENV=/app/services/agent-engine/.venv \
    PATH="/app/services/agent-engine/.venv/bin:$PATH"

WORKDIR /app

# Copy dependencies
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

# Copy code
COPY packages/eaioc-core /packages/eaioc-core
COPY packages/eaioc-database /packages/eaioc-database
COPY packages/eaioc-events /packages/eaioc-events
COPY services/agent-engine /app/services/agent-engine

WORKDIR /app/services/agent-engine

# Run as non-root
RUN useradd -m -U appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
