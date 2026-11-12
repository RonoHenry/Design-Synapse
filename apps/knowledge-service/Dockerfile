# Knowledge Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY apps/knowledge-service/requirements.txt ./requirements.txt
COPY packages/ ./packages/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY apps/knowledge-service/ ./

# Create storage directory
RUN mkdir -p /app/storage/files /app/storage/temp

# Set environment variables
ENV PYTHONPATH=/app:/app/packages
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "knowledge_service.main:app", "--host", "0.0.0.0", "--port", "8002"]
