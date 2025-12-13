# Production Dockerfile for auditorsec-platform-poc
FROM python:3.11-slim

WORKDIR /app

# Install essential dependencies
RUN pip install --no-cache-dir fastapi uvicorn psycopg2-binary

# Create minimal Python app
RUN cat > /app/main.py << 'EOF'
from fastapi import FastAPI
import os

app = FastAPI(title="AuditorSec SOC")

@app.get("/")
def root():
    return {"service": "auditorsec-platform-poc", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}
EOF

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
