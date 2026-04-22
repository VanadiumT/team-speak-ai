@echo off
setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

set "JAVA_HOME=%PROJECT_ROOT%\environment\jdk-17.0.9+9"
set "MAVEN_HOME=%PROJECT_ROOT%\environment\apache-maven-3.9.9"
set "PATH=%JAVA_HOME%\bin;%MAVEN_HOME%\bin;%PATH%"

mkdir "%PROJECT_ROOT%\logs" 2>nul

echo [1/3] Building Java project...
cd /d "%PROJECT_ROOT%\team-speak-bot"
call mvn clean package -DskipTests -q
if errorlevel 1 (
    echo Java build failed!
    pause
    exit /b 1
)
echo Java build OK

echo.
echo [2/3] Starting Java service (port 8080)...
start /b java -jar target\teamspeak-voice-bridge-1.0.0-SNAPSHOT.jar > logs\teamspeak-bridge.log 2>&1
echo Java service started

echo.
echo [3/3] Starting Python backend (port 8000)...
cd /d "%PROJECT_ROOT%\team-speak-ai\backend"
start "Python Backend" cmd /c "venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000"
echo Python backend started

echo.
echo [Bonus] Starting frontend (port 5173)...
cd /d "%PROJECT_ROOT%\team-speak-ai\frontend"
start "Vue Frontend" cmd /c "npm run dev"
echo Frontend started

echo.
echo ==========================================
echo All services started
echo ==========================================
echo.
echo Java TeamSpeak Bridge: http://localhost:8080
echo Python Backend:       http://localhost:8000
echo Vue Frontend:         http://localhost:5173
echo.
echo Logs: logs\
echo.
echo Stop: stop-all.bat
echo ==========================================
pause
