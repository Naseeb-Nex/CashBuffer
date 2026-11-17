FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY apps/ingress/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/ingress/ apps/ingress/

CMD ["python", "-m", "apps.ingress.main"]
