# Stage 1: Build agni-ui frontend
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

# Copy agni-ui package files
COPY agni-ui/package.json agni-ui/package-lock.json ./

# Install dependencies
RUN npm ci

# Copy agni-ui source files
COPY agni-ui/ ./

# Build the frontend
RUN npm run build

# Stage 2: Build Python application
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for psycopg2 and process management
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --only main --no-interaction --no-root

COPY manage.py ./
COPY config ./config
COPY cases ./cases
COPY agni ./agni
COPY static ./static
COPY templates ./templates

# Copy built frontend assets from stage 1 to Django static files
COPY --from=frontend-builder /frontend/dist ./agni/static/agni/ui

# Collect static files
RUN python manage.py collectstatic --noinput

# Copy supervisor configuration
COPY etc/docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create log directories
RUN mkdir -p /var/log/supervisor /var/log/django /var/log/agni

EXPOSE 8080

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
