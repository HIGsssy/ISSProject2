# Multi-stage Dockerfile for Django application with Tailwind CSS build

# Stage 1: Node.js CSS build
FROM node:18-alpine as css-builder

WORKDIR /app

# Copy Node.js configuration files
COPY package.json package-lock.json* tailwind.config.js postcss.config.js ./

# Install Node dependencies
RUN npm install --production=false

# Copy templates and static files so Tailwind can scan for classes
COPY templates ./templates
COPY static/css/input.css ./static/css/

# Build CSS
RUN npm run build:css

# Stage 2: Base image with Python dependencies
FROM python:3.11-slim as python-base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies (including cryptography dependencies)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Application image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_ENV=production

# Install runtime dependencies only (including cryptography runtime deps)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 appuser

# Set work directory
WORKDIR /app

# Copy Python packages from python-base stage
COPY --from=python-base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-base /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Copy compiled CSS from css-builder stage (overwrites input.css with style.css)
COPY --from=css-builder /app/static/css/style.css /app/static/css/style.css

# Create directories for static and media files
RUN mkdir -p /app/staticfiles /app/media && \
    chown -R appuser:appuser /app

# Copy entrypoint script
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Run entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "iss_portal.wsgi:application"]
