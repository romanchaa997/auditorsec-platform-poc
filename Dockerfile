# Production Dockerfile for auditorsec-platform-poc SOC Service
# Lightweight Python/FastAPI-based Security Operations Center

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY soc/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy SOC service code
COPY soc/ /app/
COPY analytics/schema.sql /app/schema.sql

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run SOC service on all interfaces
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
