FROM node:22-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt 'uvicorn[standard]>=0.34,<1.0'
COPY backend/app ./backend/app
COPY --from=frontend /build/frontend/dist ./frontend/dist
ENV PYTHONPATH=/app/backend \
    FRONTEND_DIST=/app/frontend/dist \
    NEWS_CACHE_DIR=/var/data \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
