FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and README (referenced by pyproject.toml)
COPY README.md ./
COPY src/ src/

# Install the project itself
RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["sh", "-c", "uv run uvicorn datasaurus.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
