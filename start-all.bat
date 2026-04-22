@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================
echo   TeamSpeak AI 一键启动 (Windows)
echo ==========================================
echo.

set "PROJECT_ROOT=%~dp0"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

set "JAVA_HOME=%PROJECT_ROOT%\environment\jdk-17.0.9+9"
set "MAVEN_HOME=%PROJECT_ROOT%\environment\apache-maven-3.9.9"
set "PATH=%JAVA_HOME%\bin;%MAVEN_HOME%\bin;%PATH%"

mkdir "%PROJECT_ROOT%\logs" 2>nul

echo [1/3] 编译 Java 项目...
cd /d "%PROJECT_ROOT%\team-speak-bot"
call mvn clean package -DskipTests -q
if errorlevel 1 (
    echo   Java 编译失败!
    pause
    exit /b 1
)
echo   Java 编译完成

echo.
echo [2/3] 启动 Java 服务 (端口 8080)...
start /b java -jar target\teamspeak-voice-bridge-1.0.0-SNAPSHOT.jar > logs\teamspeak-bridge.log 2>&1
echo   Java 服务已启动

echo.
echo [3/3] 启动 Python 后端 (端口 8000)...
cd /d "%PROJECT_ROOT%\team-speak-ai\backend"
start /b cmd /c "venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000 > ..\..\..\logs\python-backend.log 2>&1"
echo   Python 后端已启动

echo.
echo [Bonus] 启动前端 (端口 5173)...
cd /d "%PROJECT_ROOT%\team-speak-ai\frontend"
start /b cmd /c "npm run dev > ..\..\..\logs\frontend.log 2>&1"
echo   前端已启动

echo.
echo ==========================================
echo   所有服务已启动
echo ==========================================
echo.
echo   Java TeamSpeak Bridge: http://localhost:8080
echo   Python Backend:       http://localhost:8000
echo   Vue Frontend:         http://localhost:5173
echo.
echo   日志文件: logs\
echo.
echo   停止所有服务: stop-all.bat
echo ==========================================
echo.
echo   按任意键退出此窗口（服务继续运行）...
pause >nul
