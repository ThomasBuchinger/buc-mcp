FROM python:3.14-slim AS builder

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.14-slim

USER 1000
WORKDIR /app

COPY --from=builder /app/.venv .venv
COPY src/ src/
COPY prompts/ prompts/
COPY skills/ skills/

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
