FROM node:24-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY requirements.lock ./
COPY backend/ backend/
RUN pip install --no-cache-dir -r requirements.lock .
COPY --from=frontend /build/frontend/dist frontend/dist
RUN useradd --create-home --uid 10001 urban && chown -R urban:urban /app
USER urban
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
