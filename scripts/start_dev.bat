@echo off
echo ==========================================
echo   HOLOGRAPHIC AVATAR SYSTEM - DEV START
echo ==========================================
echo.

REM Ir al directorio del proyecto
cd /d "C:\avatar ventilador\holographic-system"

echo [1/4] Iniciando servicios Docker (PostgreSQL, Redis, MinIO)...
docker-compose up -d postgres redis minio
if errorlevel 1 (
    echo ERROR: No se pudieron iniciar los contenedores Docker
    echo Asegurate de tener Docker Desktop corriendo
    pause
    exit /b 1
)

echo Esperando a que los servicios esten listos...
timeout /t 5 /nobreak > nul

echo.
echo [2/4] Instalando dependencias del Orchestrator...
cd services\orchestrator
pip install -r requirements.txt -q

echo.
echo [3/4] Iniciando Orchestrator en puerto 8000...
start "Orchestrator" cmd /k "cd /d C:\avatar ventilador\holographic-system\services\orchestrator && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo.
echo [4/4] Iniciando servicios de procesamiento...
cd ..\frame-processor
start "Frame-Processor" cmd /k "pip install -r requirements.txt -q && python -m uvicorn main:app --host 0.0.0.0 --port 8010 --reload"

cd ..\polar-encoder
start "Polar-Encoder" cmd /k "pip install -r requirements.txt -q && python -m uvicorn main:app --host 0.0.0.0 --port 8011 --reload"

cd ..\fan-driver
start "Fan-Driver" cmd /k "pip install -r requirements.txt -q && python -m uvicorn main:app --host 0.0.0.0 --port 8012 --reload"

echo.
echo ==========================================
echo   SERVICIOS INICIADOS:
echo ==========================================
echo   - PostgreSQL:     localhost:5432
echo   - Redis:          localhost:6379
echo   - MinIO:          localhost:9000 (console: 9001)
echo   - Orchestrator:   http://localhost:8000
echo   - Frame Proc:     http://localhost:8010
echo   - Polar Encoder:  http://localhost:8011
echo   - Fan Driver:     http://localhost:8012
echo.
echo   API Docs: http://localhost:8000/docs
echo ==========================================
echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause > nul
