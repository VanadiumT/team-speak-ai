@echo off
echo Stopping all TeamSpeak AI services...
echo.

taskkill /F /IM java.exe >nul 2>&1
echo Java service stopped

taskkill /F /FI "WINDOWTITLE eq Python Backend" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Vue Frontend" >nul 2>&1
echo Python/Node services stopped

echo.
echo All services stopped
pause
