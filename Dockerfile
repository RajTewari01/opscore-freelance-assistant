FROM python:3.10-slim

WORKDIR /app

# Copy requirement files first for docker caching
COPY opscore/requirements.txt requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Expose port (Cloud Run sets $PORT dynamically, defaults to 8000 locally)
EXPOSE 8000

# Run Uvicorn using the PORT environment variable provided by Cloud Run, falling back to 8000
CMD uvicorn opscore.main:app --host 0.0.0.0 --port ${PORT:-8000}
