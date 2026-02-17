@echo off
echo ==========================================
echo   INICIANDO SERVICIOS AI (Linly-Talker)
echo ==========================================
echo.
echo NOTA: Estos servicios requieren GPU y modelos descargados
echo.

REM Verificar que existen los repos
if not exist "C:\avatar ventilador\Linly-Talker" (
    echo ERROR: No se encontro Linly-Talker en C:\avatar ventilador\Linly-Talker
    pause
    exit /b 1
)

echo [1/4] Iniciando TTS Service (puerto 8001)...
start "Linly-TTS" cmd /k "cd /d C:\avatar ventilador\Linly-Talker && python -m fastapi dev api/tts_api.py --host 0.0.0.0 --port 8001"

timeout /t 3 /nobreak > nul

echo [2/4] Iniciando LLM Service (puerto 8002)...
start "Linly-LLM" cmd /k "cd /d C:\avatar ventilador\Linly-Talker && python -m fastapi dev api/llm_api.py --host 0.0.0.0 --port 8002"

timeout /t 3 /nobreak > nul

echo [3/4] Iniciando Avatar Service (puerto 8003)...
start "Linly-Avatar" cmd /k "cd /d C:\avatar ventilador\Linly-Talker && python -m fastapi dev api/talker_api.py --host 0.0.0.0 --port 8003"

echo.
echo [4/4] Iniciando FasterLivePortrait (puerto 9871)...
if exist "C:\avatar ventilador\FasterLivePortrait" (
    start "FasterLivePortrait" cmd /k "cd /d C:\avatar ventilador\FasterLivePortrait && python api.py"
) else (
    echo ADVERTENCIA: FasterLivePortrait no encontrado, saltando...
)

echo.
echo ==========================================
echo   SERVICIOS AI INICIADOS:
echo ==========================================
echo   - TTS:              http://localhost:8001
echo   - LLM:              http://localhost:8002
echo   - Avatar:           http://localhost:8003
echo   - LivePortrait:     http://localhost:9871
echo ==========================================
echo.
pause
