# Multi-stage build para optimizar tamaño de imagen
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app ./app

# Download voices from GitHub repository during build
# Note: This downloads voice files during the build, not at runtime
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    mkdir -p voices && \
    cd voices && \
    git init && \
    git remote add origin https://github.com/microsoft/VibeVoice.git && \
    git config core.sparseCheckout true && \
    echo "demo/voices/streaming_model/*.pt" >> .git/info/sparse-checkout && \
    git pull --depth=1 origin main && \
    mv demo/voices/streaming_model . && \
    rm -rf demo .git && \
    cd .. && \
    apt-get remove -y git && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (Cloud Run will inject PORT automatically)
EXPOSE 8080

# Start server
# Cloud Run provides PORT env variable automatically
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1
