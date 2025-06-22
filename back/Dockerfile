FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/uploads /app/logs

# Copy only source code (not .venv, logs, etc)
COPY src/ ./src/
COPY .env* ./

# Expose port
EXPOSE 8000

# Command to run the application (sin --reload en producción)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--ws", "websockets"]