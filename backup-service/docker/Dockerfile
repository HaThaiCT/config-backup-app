# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt


# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Create necessary directories
RUN mkdir -p /backups /var/log/backup-service /etc/backup-service

# Copy application code
COPY src/ ./src/
COPY config/config.example.yaml /etc/backup-service/config.yaml

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV BACKUP_CONFIG=/etc/backup-service/config.yaml

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command: start service
ENTRYPOINT ["python", "-m", "src.main"]
CMD []
