FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev \
    --index-url=http://host.docker.internal:3141/root/internal/+simple/

COPY src/ ./src/

ARG APP_VERSION=dev
LABEL version=${APP_VERSION}
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["uv", "run", "python", "-m", "src.cli.main"]
CMD ["--help"]
