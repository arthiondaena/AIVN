# Use a base image with Python
FROM python:3.12-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED=True

# Install uv
RUN pip install --no-cache-dir uv

# Set the working directory for the application
WORKDIR /app

# Copy the requirements file first (to cache dependencies layer)
COPY pyproject.toml uv.lock* /app/

# Install dependencies
RUN uv sync

# Copy the FastAPI application code
COPY . /app/

EXPOSE 8000

# Command to run the app using Uvicorn
# We use the PORT environment variable provided by Cloud Run.
CMD ["sh", "-c", "uv run uvicorn api_app:app --host 0.0.0.0 --port ${PORT:-8000}"]