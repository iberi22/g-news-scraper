# Use an official Python runtime as a parent image
FROM python:3.11-slim as builder

# Set the working directory
WORKDIR /app

# Install build essentials needed for some Python packages
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential

# Install pipenv (if using Pipfile) or just copy requirements
COPY requirements.txt .

# Install dependencies
# Using --no-cache-dir reduces image size
# Using virtualenv to isolate dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Final Stage ---
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the virtualenv from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code
COPY ./app /app

# Make port 8080 available to the world outside this container
# Cloud Run expects the container to listen on the port defined by the PORT env var ($PORT), default 8080
EXPOSE 8080

# Define environment variable for the port
ENV PORT=8080

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Run the application using Gunicorn
# Gunicorn is the recommended WSGI server for production Flask apps
# Use the number of workers recommended by Gunicorn based on CPU cores (or start with a fixed number)
# Use the PORT environment variable provided by Cloud Run
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app.main:app
