# Use official Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements
COPY backend/requirements.txt ./backend/requirements.txt

# Install playwright dependencies
RUN apt-get update && apt-get install -y \
    chromium-driver \
    chromium \
    libgbm-dev \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxi6 \
    libxtst6 \
    libasound2 \
    wget \
    ca-certificates \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Install Python deps and playwright
COPY backend/ ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt && \
    playwright install --with-deps && \
    rm -rf /root/.cache

# Copy application code
COPY backend/ ./backend/
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=0

# Expose port
EXPOSE 8000

# Run the app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]