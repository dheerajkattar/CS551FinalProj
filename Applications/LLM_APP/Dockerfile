FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Set environment variables
ENV GEMINI_API_KEY=${GEMINI_API_KEY}

# Expose port
EXPOSE 5003

# Run the application
CMD ["python", "main.py"]
