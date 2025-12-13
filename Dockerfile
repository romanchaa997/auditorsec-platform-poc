# Production Dockerfile for auditorsec-platform-poc
# Runs the complete stack with docker-compose orchestration

FROM docker:latest

# Install docker-compose
RUN apk add --no-cache python3 py3-pip && \
    pip3 install docker-compose

# Copy project files
WORKDIR /app
COPY . .

# Expose ports for all services
EXPOSE 8000 3000 5432

# Health check for the main API
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start all services using docker-compose
CMD ["docker-compose", "up"]
