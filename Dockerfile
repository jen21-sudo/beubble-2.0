FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Install system dependencies and required fonts for headless browser rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget ca-certificates curl gnupg fonts-unifont \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 libxshmfence1 libnspr4 \
    && rm -rf /var/lib/apt/lists/*

# Copy package descriptors and upgrade pip framework dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Download pure Chromium binary packages bypassing operating system constraints
RUN playwright install chromium

# Replicate host project environment mapping backend files securely
COPY backend/ ./backend/
COPY frontend/ ./frontend/

EXPOSE 8000

# Execute server initialization tracking the native backend module context
CMD ["sh", "-c", "cd /app/backend && uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info"]
