@echo off
echo ==========================================
echo   WEBCAM A VENTILADOR HOLOGRAFICO
echo ==========================================
echo.
echo Asegurate de:
echo   1. Estar conectado al WiFi del ventilador
echo   2. Tener la webcam conectada
echo.

cd /d "%~dp0"

python webcam_to_fan.py --fan-ip 192.168.4.1 --camera 0

pause
