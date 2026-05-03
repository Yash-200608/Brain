# syntax=docker/dockerfile:1.6
FROM python:3.11-slim AS base

WORKDIR /app

# system deps for chromadb/sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential git && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8000
CMD ["python", "main.py", "api"]
