# Stage 1: Build Vue frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --registry=https://mirrors.huaweicloud.com/repository/npm/
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + serve frontend static files
FROM python:3.12-slim
WORKDIR /app

# Install system deps (none needed beyond slim image)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy built frontend static files from stage 1
COPY --from=frontend-builder /app/frontend/dist ./static

# Data directory for SQLite and encryption key
RUN mkdir -p /app/data
ENV DATABASE_URL=sqlite+aiosqlite:////app/data/automation.db
ENV STATIC_DIR=/app/static

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
