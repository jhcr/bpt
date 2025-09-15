FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv

COPY shared/python/pyproject.toml ./opt/shared/pyproject.toml
COPY shared/python/src ./opt/shared/src
RUN uv pip install -e ./opt/shared --system

COPY apps/bff/pyproject.toml ./
RUN uv pip install --system --no-cache-dir -e .

COPY apps/bff/ ./

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

RUN echo '#!/bin/bash\nexport PYTHONPATH=/app\ncd /app\nexec python -m uvicorn presentation.app:app --host 0.0.0.0 --port 8080' > /start.sh && chmod +x /start.sh

CMD ["/start.sh"]