FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install -r backend/requirements.txt
COPY backend/fleettrack_api backend/fleettrack_api
EXPOSE 8000
CMD ["uvicorn", "fleettrack_api.main:app", "--app-dir", "/app/backend", "--host", "0.0.0.0", "--port", "8000"]
