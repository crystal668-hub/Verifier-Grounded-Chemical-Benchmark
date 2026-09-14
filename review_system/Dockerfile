FROM node:24-bookworm-slim AS frontend
WORKDIR /app
COPY review_system/frontend/package.json review_system/frontend/package-lock.json* ./
RUN npm ci
COPY review_system/frontend ./
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY review_system/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY review_system/backend ./backend
COPY --from=frontend /app/dist ./frontend/dist
COPY src ./src
ENV PYTHONPATH=/app/src:/app/backend
EXPOSE 8000
CMD ["sh","-c","cd /app/backend && alembic -c alembic.ini upgrade head && exec uvicorn review_system.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
