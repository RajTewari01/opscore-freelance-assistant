# ============= Stage 1: Build Next.js Frontend =============
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./

# Production build — outputs standalone server
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ============= Stage 2: Production Runtime =============
FROM python:3.10-slim

WORKDIR /app

# Install Node.js for Next.js standalone server
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl supervisor && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY opscore/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY opscore/ opscore/
COPY main.py .

# Copy built frontend
COPY --from=frontend-builder /frontend/.next/standalone /app/frontend-server
COPY --from=frontend-builder /frontend/.next/static /app/frontend-server/.next/static
COPY --from=frontend-builder /frontend/public /app/frontend-server/public

# Supervisor config to run both processes
COPY supervisord.conf /etc/supervisord.conf

EXPOSE 8080

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
