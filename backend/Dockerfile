FROM python:3.12-slim

# Install system dependencies for browser and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend package metadata and install dependencies
COPY backend/pyproject.toml ./backend/
COPY backend/__init__.py ./backend/
COPY backend/app/__init__.py ./backend/app/
COPY backend/worker/__init__.py ./backend/worker/

RUN pip install --no-cache-dir ./backend/[scraper]

# Install Patchright Chromium browser + OS deps
# Patchright uses the same install commands as Playwright
RUN patchright install chromium && patchright install-deps chromium

# Copy all source code (overridden by volume mount in dev)
COPY backend/ ./backend/
