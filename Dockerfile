# 📄 File: Dockerfile
#
# 🧭 Purpose (Layman Explanation):
# Instructions for building a containerized version of our Plant Care app
# that can run consistently anywhere, like a complete recipe with ingredients.
#
# 🧪 Purpose (Technical Summary):
# Multi-stage Dockerfile for FastAPI application with optimized layers for
# development and production environments, including health checks and security.
#
# 🔗 Dependencies:
# - Python 3.11+ base image
# - requirements.txt for Python packages
# - Application source code
#
# 🔄 Connected Modules / Calls From:
# - docker-compose.yml services
# - CI/CD build pipelines
# - Kubernetes deployments
# - Local development environment

# =============================================================================
# BASE IMAGE CONFIGURATION
# =============================================================================
ARG PYTHON_VERSION=3.11.8
FROM python:${PYTHON_VERSION}-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    libmagic1 \
    libmagic-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r plantcare && useradd -r -g plantcare plantcare

# =============================================================================
# DEPENDENCIES STAGE
# =============================================================================
FROM base as dependencies

# Copy requirements first (for better caching)
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# =============================================================================
# DEVELOPMENT STAGE
# =============================================================================
FROM dependencies as development

# Install development dependencies
RUN pip install pytest pytest-asyncio pytest-mock black isort mypy pre-commit

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/uploads /app/temp && \
    chown -R plantcare:plantcare /app/logs /app/uploads /app/temp

# Set permissions
RUN chmod +x scripts/*.sh 2>/dev/null || true

# Switch to non-root user
USER plantcare

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "info"]

# =============================================================================
# PRODUCTION DEPENDENCIES STAGE
# =============================================================================
FROM base as production-deps

# Copy requirements
COPY requirements.txt ./

# Install only production dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-dev -r requirements.txt && \
    pip cache purge

# =============================================================================
# PRODUCTION STAGE
# =============================================================================
FROM production-deps as production

# Copy application code
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY alembic.ini ./

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/uploads /app/temp && \
    chown -R plantcare:plantcare /app && \
    chmod 755 /app/logs /app/uploads /app/temp

# Install gunicorn for production
RUN pip install gunicorn uvloop httptools

# Remove unnecessary files
RUN find /app -name "*.pyc" -delete && \
    find /app -name "__pycache__" -type d -exec rm -rf {} + && \
    find /app -name "*.pyo" -delete

# Switch to non-root user
USER plantcare

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command for production
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]

# =============================================================================
# CELERY WORKER STAGE
# =============================================================================
FROM production-deps as celery

# Copy application code
COPY app/ ./app/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create necessary directories
RUN mkdir -p /app/logs /app/temp && \
    chown -R plantcare:plantcare /app

# Switch to non-root user
USER plantcare

# Health check for Celery worker
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD celery -A app.background_jobs.celery_app inspect ping || exit 1

# Default command for Celery worker
CMD ["celery", "-A", "app.background_jobs.celery_app", "worker", "--loglevel=info"]

# =============================================================================
# ADMIN PANEL STAGE (React)
# =============================================================================
FROM node:18-alpine as admin-build

WORKDIR /app

# Copy package files
COPY admin_panel/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY admin_panel/ ./

# Build for production
RUN npm run build

# =============================================================================
# ADMIN PANEL PRODUCTION
# =============================================================================
FROM nginx:1.25-alpine as admin-production

# Copy built assets
COPY --from=admin-build /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY docker/nginx/admin.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost || exit 1

EXPOSE 80

# =============================================================================
# BUILD ARGUMENTS & LABELS
# =============================================================================
ARG BUILD_DATE
ARG VERSION
ARG VCS_REF

# Add labels
LABEL maintainer="Plant Care Team <dev@plantcare.app>" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="plant-care-backend" \
      org.label-schema.description="AI-Powered Plant Care Management System - Backend API" \
      org.label-schema.version=$VERSION \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/plantcare/backend" \
      org.label-schema.schema-version="1.0"