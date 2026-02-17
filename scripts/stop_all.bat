@echo off
echo Deteniendo servicios del Holographic Avatar System...

REM Matar procesos de uvicorn
taskkill /F /FI "WINDOWTITLE eq Orchestrator*" 2>nul
taskkill /F /FI "WINDOWTITLE eq Frame-Processor*" 2>nul
taskkill /F /FI "WINDOWTITLE eq Polar-Encoder*" 2>nul
taskkill /F /FI "WINDOWTITLE eq Fan-Driver*" 2>nul
taskkill /F /FI "WINDOWTITLE eq Linly-*" 2>nul
taskkill /F /FI "WINDOWTITLE eq FasterLivePortrait*" 2>nul

REM Detener Docker containers
cd /d "C:\avatar ventilador\holographic-system"
docker-compose down

echo.
echo Todos los servicios detenidos.
pause
