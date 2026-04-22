#!/bin/bash

# TeamSpeak AI 一键启动脚本
# 用法: ./start-all.sh

set -e

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 环境变量
export JAVA_HOME="$PROJECT_ROOT/environment/jdk-17.0.9+9"
export MAVEN_HOME="$PROJECT_ROOT/environment/apache-maven-3.9.9"
export PATH="$JAVA_HOME/bin:$MAVEN_HOME/bin:$PATH"

echo "=========================================="
echo "  TeamSpeak AI 一键启动"
echo "=========================================="
echo ""

# 1. 编译 Java 项目
echo "[1/3] 编译 Java 项目..."
cd "$PROJECT_ROOT/team-speak-bot"
mvn clean package -DskipTests -q
echo "  Java 编译完成"

# 2. 启动 Java TeamSpeak Voice Bridge
echo "[2/3] 启动 Java 服务 (端口 8080)..."
java -jar target/teamspeak-voice-bridge-1.0.0-SNAPSHOT.jar > logs/teamspeak-bridge.log 2>&1 &
JAVA_PID=$!
echo "  Java 服务 PID: $JAVA_PID"

# 3. 启动 Python 后端
echo "[3/3] 启动 Python 后端 (端口 8000)..."
cd "$PROJECT_ROOT/team-speak-ai/backend"
./venv/Scripts/python -m uvicorn main:app --host 0.0.0.0 --port 8000 > ../../logs/python-backend.log 2>&1 &
PYTHON_PID=$!
echo "  Python 后端 PID: $PYTHON_PID"

# 4. 启动前端
echo ""
echo "[Bonus] 启动前端 (端口 5173)..."
cd "$PROJECT_ROOT/team-speak-ai/frontend"
npm run dev > ../../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "  前端 PID: $FRONTEND_PID"

# 保存 PIDs
echo "$JAVA_PID" > "$PROJECT_ROOT/logs/app.pid"
echo "$PYTHON_PID" >> "$PROJECT_ROOT/logs/app.pid"
echo "$FRONTEND_PID" >> "$PROJECT_ROOT/logs/app.pid"

echo ""
echo "=========================================="
echo "  所有服务已启动"
echo "=========================================="
echo ""
echo "  Java TeamSpeak Bridge: http://localhost:8080"
echo "  Python Backend:       http://localhost:8000"
echo "  Vue Frontend:         http://localhost:5173"
echo ""
echo "  日志文件: logs/"
echo ""
echo "  停止所有服务: ./stop-all.sh"
echo "=========================================="
