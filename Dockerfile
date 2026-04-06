FROM python:3.10-slim-bullseye

WORKDIR /app

# Install system dependencies and clean up to save space
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends git curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Set permissions for the start script
RUN chmod +x start.sh

# Run the bot
CMD ["bash", "start.sh"]
