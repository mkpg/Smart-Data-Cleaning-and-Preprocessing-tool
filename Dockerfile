FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (libmagic for file type detection)
RUN apt-get update && apt-get install -y \
    gcc \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure the uploads directory exists at runtime
RUN mkdir -p web/uploads/audit_exports \
             web/uploads/review_store

# Expose port (Render overrides with $PORT env var via gunicorn -b)
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health').read()"

# Production server — 2 workers, 300s timeout for large file processing
CMD ["gunicorn", \
     "--chdir", "web", \
     "--workers=2", \
     "--timeout=300", \
     "--bind=0.0.0.0:5000", \
     "--access-logfile=-", \
     "--error-logfile=-", \
     "server:app"]
