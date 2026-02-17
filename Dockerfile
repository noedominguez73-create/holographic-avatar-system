FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements del orchestrator
COPY services/orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del orchestrator
COPY services/orchestrator/app ./app

# Copiar integraciones
COPY integrations ./integrations

# Puerto dinámico de Railway
ENV PORT=8000
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Comando - usa variable PORT de Railway
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
