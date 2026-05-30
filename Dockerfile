FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DB_PATH=/app/data/netfly.db

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# SQLite database lives on a mounted volume so it survives image rebuilds.
RUN mkdir -p /app/data \
 && useradd -r -u 10001 netfly \
 && chown -R netfly:netfly /app
VOLUME ["/app/data"]
USER netfly

CMD ["python", "bot.py"]
