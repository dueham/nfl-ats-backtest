FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app.py .

# Create data directory (Railway will mount volume here)
RUN mkdir -p /data

# Environment defaults
ENV BETS_FILE_PATH=/data/bets.csv
ENV PYTHONUNBUFFERED=1

# Railway sets PORT env var dynamically
EXPOSE 8080

# Streamlit config for Railway
CMD streamlit run app.py \
    --server.port=${PORT:-8080} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
