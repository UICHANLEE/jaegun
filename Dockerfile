# Jaegun API + 정적 UI (커뮤니티·관리자)
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY README.md ./
COPY src ./src
COPY static ./static

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV JAEGUN_PROJECT_ROOT=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["sh", "-c", "exec uvicorn jaegun.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
