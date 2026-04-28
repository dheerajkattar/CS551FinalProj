FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5003 \
    UVICORN_WORKERS=2

EXPOSE 5003

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-5003} --workers ${UVICORN_WORKERS:-2}"]
