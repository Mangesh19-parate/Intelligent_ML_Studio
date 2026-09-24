FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (git for code version capture, build-essential for any compiled wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt requirements.lock* ./
RUN if [ -f requirements.lock ]; then pip install --no-cache-dir -r requirements.lock; else pip install --no-cache-dir -r requirements.txt; fi

# Copy backend application code
COPY . .

# Ensure storage directory exists and start script is executable
RUN mkdir -p /data/datasets && chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]

