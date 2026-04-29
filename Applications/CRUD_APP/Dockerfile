FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Cloud Run requires PORT env var (default 8080, but we use 5000)
ENV PORT=5000

# Expose port
EXPOSE $PORT

# Run the application
CMD exec python main.py
