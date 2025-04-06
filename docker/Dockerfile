# Base image
FROM python:3.12-slim

# Working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-utils \
    netcat-openbsd \
    curl \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*


# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into the working directory (root directory for your data)
COPY . .

# Add wait-for-it script
COPY wait-for-it.sh /app/wait-for-it.sh
RUN chmod +x /app/wait-for-it.sh

# Set the command to wait for the database before running the app
CMD ["bash", "-c", "/app/wait-for-it.sh db:5432 -- python init_db.py && uvicorn main:app --host 0.0.0.0 --port 8000"]