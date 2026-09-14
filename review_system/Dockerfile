FROM node:24-bookworm-slim@sha256:ba849c60be29959425b8734d57b8b4b7d56f98edd9504c9af091d5281095a71e AS frontend
WORKDIR /app
COPY review_system/frontend/package.json review_system/frontend/package-lock.json* ./
RUN npm ci
COPY review_system/frontend ./
RUN npm run build

FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254
ARG REVIEW_SOURCE_COMMIT=working-tree
WORKDIR /app
COPY review_system/backend/requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY review_system/backend ./backend
COPY --from=frontend /app/dist ./frontend/dist
COPY src ./src
ENV PYTHONPATH=/app/src:/app/backend REVIEW_SOURCE_COMMIT=${REVIEW_SOURCE_COMMIT}
EXPOSE 8000
CMD ["sh","-c","cd /app/backend && alembic -c alembic.ini upgrade head && exec uvicorn review_system.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
