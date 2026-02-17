@echo off
echo ==========================================
echo   TEST DE CONEXION CON VENTILADOR
echo ==========================================
echo.
echo Asegurate de estar conectado a la red WiFi
echo del ventilador (HoloFan, 3D-Fan, etc.)
echo.

cd /d "C:\avatar ventilador\holographic-system\scripts"

if "%1"=="" (
    python test_fan_connection.py 192.168.4.1
) else (
    python test_fan_connection.py %1
)

pause
