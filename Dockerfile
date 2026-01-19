FROM python:3.11-slim AS base

# ---- System configuration ----
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies (no extra recommends, smaller image)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        tesseract-ocr \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# ---- Python dependencies (use cache layers) ----
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ---- Application code ----
COPY . .

# NOTE:
# - Les identifiants Google (credential.json) sont montés par docker-compose
#   via un volume. On n'effectue PAS de COPY ici pour éviter d'inclure
#   des secrets dans l'image.
# - La variable d'environnement GOOGLE_APPLICATION_CREDENTIALS est
#   configurée dans docker-compose.

# Optionnel : exposer un port si vous lancez une API HTTP
# EXPOSE 8000

# ---- Default command ----
CMD ["python", "-u", "main.py"]
