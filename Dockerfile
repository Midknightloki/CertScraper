FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for wkhtmltopdf and Playwright
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Install Playwright browsers and their dependencies
RUN playwright install --with-deps chromium

EXPOSE 8000

# Using Gunicorn to run the FastAPI app (backend/main.py)
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "backend.main:app", "--bind", "0.0.0.0:8000"]