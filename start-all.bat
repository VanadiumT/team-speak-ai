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
echo [2/3] Launching all services in Windows Terminal tabs...

wt.exe -w 0 new-tab --title "Java Bridge :8080" cmd /k "cd /d "%PROJECT_ROOT%\team-speak-bot" && java -jar target\teamspeak-voice-bridge-1.0.0-SNAPSHOT.jar" ; new-tab --title "Python Backend :8000" cmd /k "cd /d "%PROJECT_ROOT%\team-speak-ai\backend" && venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000" ; new-tab --title "Vue Frontend :5173" cmd /k "cd /d "%PROJECT_ROOT%\team-speak-ai\frontend" && npm run dev"

echo.
echo ==========================================
echo All services started in Windows Terminal
echo ==========================================
echo.
echo Java TeamSpeak Bridge: http://localhost:8080
echo Python Backend:       http://localhost:8000
echo Vue Frontend:         http://localhost:5173
echo.
echo Stop: stop-all.bat
echo ==========================================
pause
