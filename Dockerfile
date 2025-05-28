# arielle_backend/Dockerfile
FROM python:3.12.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc

# COPY backend ./backend
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000 8500