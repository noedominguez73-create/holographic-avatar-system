FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema (sin FFmpeg dev - PyAV usa su propio FFmpeg embebido)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements del orchestrator
COPY services/orchestrator/requirements.txt ./requirements.txt
# Forzar uso de wheels precompilados para av (evita compilación contra FFmpeg del sistema)
RUN pip install --no-cache-dir --only-binary av -r requirements.txt

# Copiar código del orchestrator
COPY services/orchestrator/app ./app

# Copiar integraciones
COPY integrations ./integrations

# Puerto dinámico de Railway
ENV PORT=8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Comando - usa variable PORT de Railway
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
