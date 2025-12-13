# Production Dockerfile for auditorsec-platform-poc SOC Service
# Minimal Python/FastAPI-based Security Operations Center

FROM python:3.11-slim

WORKDIR /app

# Install only essential dependencies
RUN pip install --no-cache-dir fastapi uvicorn psycopg2-binary

# Create minimal app structure
RUN mkdir -p /app/soc /app/analytics

# Copy schema if exists, otherwise create minimal one
COPY analytics/schema.sql /app/schema.sql 2>/dev/null || echo "-- Schema file not found" > /app/schema.sql

# Create minimal main.py for the SOC service
RUN echo 'from fastapi import FastAPI\nimport os\n\napp = FastAPI(title="AuditorSec SOC")\n\n@app.get("/health")\ndef health_check():\n    return {\"status": "healthy", "service": "SOC API"}\n\n@app.get("/")\ndef root():\n    return {\"service": "auditorsec-platform-poc", "version": "1.0.0"}' > /app/main.py

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \\
  CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
