FROM python:3.12-slim

# Avoid interactive dialogs
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies: FFmpeg, Xvfb, and Chromium libraries for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    xvfb \
    ca-certificates \
    curl \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency requirements
COPY requirements.txt .

# Install python dependencies and lucidadl
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir lucidadl playwright

# Install playwright browser
RUN python -m playwright install --with-deps chromium

# Copy app code
COPY . .

# Ensure scripts have execute permissions
RUN chmod +x scripts/*.sh

# Persist Lucida session state & SQLite database
VOLUME ["/root/.local/share/lucidadl", "/app/data"]

CMD ["python", "-m", "bot.main"]
