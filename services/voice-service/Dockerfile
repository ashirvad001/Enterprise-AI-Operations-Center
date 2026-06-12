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

# Copy voice-service
COPY services/voice-service/pyproject.toml services/voice-service/poetry.lock* ./services/voice-service/
WORKDIR /app/services/voice-service

# Install dependencies
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

# Runtime Stage
FROM python:3.11-slim-bookworm as runtime

ENV VIRTUAL_ENV=/app/services/voice-service/.venv \
    PATH="/app/services/voice-service/.venv/bin:$PATH"

WORKDIR /app

# Copy dependencies
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

# Copy code
COPY packages/eaioc-core /packages/eaioc-core
COPY services/voice-service /app/services/voice-service

WORKDIR /app/services/voice-service

# Run as non-root
RUN useradd -m -U appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8006

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006"]
