FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /api

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./api /api

# Expose port
EXPOSE 8080

# Command to run application
CMD ["uvicorn", "main:api", "--host", "0.0.0.0", "--port", "8080"]
