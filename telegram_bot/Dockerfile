FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system dependencies (if any needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY app.py ./

# Copy .env if you want to build with secrets (optional, or mount at runtime)
# COPY .env ./

# Run the bot
CMD ["python", "app.py"]

