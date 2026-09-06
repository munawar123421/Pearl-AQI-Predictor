# Dockerfile for Pearls AQI Predictor

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/raw data/processed data/features data/models data/reports

# Expose ports
EXPOSE 8000 8501

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEMO_MODE=true
ENV DATA_PROVIDER=mock

# Default command (can be overridden)
CMD ["uvicorn", "src.pearls_aqi.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
