@echo off
echo ==========================================
echo   INICIANDO KIOSK DE AVATAR HOLOGRAFICO
echo ==========================================
echo.

REM Iniciar servidor web simple
cd /d "C:\avatar ventilador\holographic-system\kiosk-app"

echo Iniciando servidor web en http://localhost:8080
echo.
echo Abre esta URL en Chrome en modo kiosco:
echo   chrome.exe --kiosk http://localhost:8080
echo.
echo O en modo normal:
echo   http://localhost:8080
echo.

python -m http.server 8080

pause
