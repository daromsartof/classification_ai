# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y build-essential tesseract-ocr libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code
COPY . /app/

# Copy credentials (if needed for Google APIs)
COPY credential.json /app/credential.json

# Set environment variable for Google credentials (can be overridden)
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/credential.json

# Expose port if needed (uncomment if running a web server)
# EXPOSE 8000

# Default command
CMD ["python", "main.py"] 
