@echo off
chcp 65001 >nul
echo 停止所有 TeamSpeak AI 服务...
echo.

taskkill /F /IM java.exe >nul 2>&1
echo   Java 服务已停止

taskkill /F /IM python.exe >nul 2>&1
echo   Python 后端已停止

taskkill /F /IM node.exe >nul 2>&1
echo   前端已停止

echo.
echo 所有服务已停止
pause
