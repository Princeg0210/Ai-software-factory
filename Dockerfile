# Secure, Hardened Dockerfile for AI Software Factory (ASF)
FROM python:3.12-slim

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# Install core build dependencies, git, and libpq for postgres
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Add non-root security user
RUN useradd -m -s /bin/bash sandbox

WORKDIR /workspace

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .
RUN chown -R sandbox:sandbox /workspace

# Switch to non-root sandbox execution user
USER sandbox

# Default execution entrypoint for web API
EXPOSE 8000
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
