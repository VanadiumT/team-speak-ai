#!/bin/bash

# TeamSpeak AI 停止脚本
# 用法: ./stop-all.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$PROJECT_ROOT/logs/app.pid"

if [ -f "$PID_FILE" ]; then
    echo "停止所有服务..."
    while read -r pid; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null && echo "  已停止 PID: $pid" || true
        fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
    echo "所有服务已停止"
else
    echo "未找到 PID 文件，尝试直接杀进程..."
    pkill -f "teamspeak-voice-bridge" 2>/dev/null || true
    pkill -f "uvicorn main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    echo "已执行清理"
fi
