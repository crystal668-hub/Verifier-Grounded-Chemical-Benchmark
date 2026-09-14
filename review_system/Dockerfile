FROM node:22-alpine AS frontend
WORKDIR /app
COPY review_system/frontend/package.json review_system/frontend/package-lock.json* ./
RUN npm install
COPY review_system/frontend ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY review_system/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY review_system/backend ./backend
COPY --from=frontend /app/dist ./frontend/dist
COPY src ./src
ENV PYTHONPATH=/app/src:/app/backend
EXPOSE 8000
CMD ["uvicorn","review_system.main:app","--app-dir","backend","--host","0.0.0.0","--port","8000"]
