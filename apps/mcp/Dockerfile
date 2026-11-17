FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY apps/mcp/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/mcp/ apps/mcp/

EXPOSE 8080

CMD ["python", "-m", "apps.mcp.runner", "--transport", "sse", "--host", "0.0.0.0", "--port", "8080"]
