@echo off
echo Stopping all TeamSpeak AI services...
echo.

taskkill /F /IM java.exe >nul 2>&1
echo Java service stopped

taskkill /F /IM python.exe >nul 2>&1
echo Python backend stopped

taskkill /F /IM node.exe >nul 2>&1
echo Node services stopped

echo.
echo All services stopped
pause
