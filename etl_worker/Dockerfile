FROM python:3.11-slim

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY src/ ./src/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_REGION=us-west-1

# Run the ETL worker
CMD ["python", "main.py"]
