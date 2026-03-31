# GodsEye Worker Service - Python Service
# Executes scraping jobs with Burn & Rotate strategy

FROM mcr.microsoft.com/playwright/python:v1.57.0-jammy

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create profiles directory for Burn & Rotate strategy
RUN mkdir -p /app/profiles

# Environment variables
ENV PYTHONPATH=/app

# Playwright browsers are pre-installed in the official image
# No manual installation needed

# Default command
CMD ["python", "worker_batch.py"]
# # CMD ["python", "worker_main.py"]
