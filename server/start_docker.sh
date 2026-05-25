#!/bin/bash
# QuantClaw Docker 环境启动脚本
# 在 Docker 容器内启动两个服务

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Starting QuantClaw Services in Docker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查是否在容器内
if [ ! -f "/home/node/.openclaw/openclaw.json" ]; then
    echo "❌ Error: Not running in Docker container"
    echo "   This script should be run inside the OpenClaw container"
    exit 1
fi

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

echo "✅ Python: $(python3 --version)"

# 检查并安装依赖
echo "🔍 Checking dependencies..."

# 检查所有必需的依赖
MISSING_DEPS=""
python3 -c "import aiohttp" 2>/dev/null || MISSING_DEPS="$MISSING_DEPS aiohttp"
python3 -c "import requests" 2>/dev/null || MISSING_DEPS="$MISSING_DEPS requests"
python3 -c "import numpy" 2>/dev/null || MISSING_DEPS="$MISSING_DEPS numpy"

if [ -n "$MISSING_DEPS" ]; then
    echo "⚠️  Missing dependencies:$MISSING_DEPS"
    echo "   Installing..."
    
    # 转换为 apt 包名
    APT_DEPS=$(echo "$MISSING_DEPS" | sed 's/\baiohttp\b/python3-aiohttp/g; s/\brequests\b/python3-requests/g; s/\bnumpy\b/python3-numpy/g')
    
    # 尝试使用 apt 安装（推荐）
    if command -v apt-get &> /dev/null; then
        echo "   Using apt-get (requires root)..."
        apt-get update -qq && apt-get install -y -qq $APT_DEPS && echo "   ✓ Installed via apt" || {
            echo "   ⚠️  apt-get failed, trying pip..."
            python3 -m pip install --break-system-packages $MISSING_DEPS && echo "   ✓ Installed via pip" || {
                echo "❌ Failed to install dependencies"
                exit 1
            }
        }
    else
        # 尝试使用 pip
        echo "   Using pip..."
        python3 -m pip install --break-system-packages $MISSING_DEPS || {
            echo "❌ Failed to install dependencies"
            exit 1
        }
    fi
else
    echo "✅ All dependencies OK"
fi

# 最终检查所有依赖是否可用
if ! python3 -c "import aiohttp, requests, numpy" 2>/dev/null; then
    echo "❌ Some dependencies are not available!"
    echo "   Please install manually:"
    echo "   sudo docker exec -u root <container> apt-get update && apt-get install -y python3-aiohttp python3-requests python3-numpy"
    exit 1
fi

# 获取工作目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 加载环境变量
if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo "✅ Loaded .env"
fi

# 确保 Docker 数据目录存在
DATA_DOCKER_DIR="${QUANTCLAW_DATA_DIR:-/home/node/quantclaw/server/data-docker}"
mkdir -p "$DATA_DOCKER_DIR"
echo "✅ Data directory: $DATA_DOCKER_DIR"

# 获取 GATEWAY_TOKEN (从 openclaw.json)
if [ -z "$GATEWAY_TOKEN" ]; then
    GATEWAY_TOKEN=$(python3 -c "import json; print(json.load(open('/home/node/.openclaw/openclaw.json'))['gateway']['auth']['token'])" 2>/dev/null)
fi

if [ -z "$GATEWAY_TOKEN" ]; then
    echo "❌ GATEWAY_TOKEN not found"
    exit 1
fi

echo "✅ GATEWAY_TOKEN: ${GATEWAY_TOKEN:0:20}..."

# 停止旧进程（如果存在）
echo ""
echo "🔍 Checking for existing processes..."
pkill -f "quantclaw_webhook.py" 2>/dev/null && echo "  ✓ Stopped old quantclaw_webhook" || true
pkill -f "app_docker.py" 2>/dev/null && echo "  ✓ Stopped old app_docker" || true
sleep 2

# 启动认证服务 (端口 8081)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 Starting Authentication Service (port 8081)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

export PORT=8081
nohup python3 quantclaw_webhook.py > /tmp/quantclaw_webhook.log 2>&1 &
AUTH_PID=$!
echo "   PID: $AUTH_PID"
echo "   Log: /tmp/quantclaw_webhook.log"

# 等待认证服务启动
sleep 3

# 检查认证服务
if ! kill -0 $AUTH_PID 2>/dev/null; then
    echo "❌ Authentication service failed to start"
    echo ""
    echo "Last 20 lines of log:"
    tail -20 /tmp/quantclaw_webhook.log
    exit 1
fi

# 健康检查
if curl -s http://localhost:8081/health > /dev/null 2>&1; then
    echo "✅ Authentication service healthy"
else
    echo "⚠️  Health check failed (service may still be starting)"
fi

# 启动主服务 (端口 8080)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Starting Main Service (port 8080)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

export PORT=8080
export AUTH_SERVICE_URL="http://127.0.0.1:8081"
export GATEWAY_TOKEN="$GATEWAY_TOKEN"
nohup python3 app_docker.py > /tmp/app_docker.log 2>&1 &
APP_PID=$!
echo "   PID: $APP_PID"
echo "   Log: /tmp/app_docker.log"

# 等待主服务启动
sleep 3

# 检查主服务
if ! kill -0 $APP_PID 2>/dev/null; then
    echo "❌ Main service failed to start"
    echo ""
    echo "Last 20 lines of log:"
    tail -20 /tmp/app_docker.log
    kill $AUTH_PID 2>/dev/null
    exit 1
fi

# 健康检查
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ Main service healthy"
else
    echo "⚠️  Health check failed (service may still be starting)"
fi

# 保存 PIDs
echo "$AUTH_PID" > /tmp/quantclaw_auth.pid
echo "$APP_PID" > /tmp/quantclaw_app.pid

# 显示状态
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All Services Started Successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Authentication Service (quantclaw_webhook.py)"
echo "   Container Port: 8081"
echo "   PID: $AUTH_PID"
echo "   Health: http://localhost:8081/health"
echo ""
echo "📍 Main Service (app_docker.py)"
echo "   Container Port: 8080"
echo "   Host Port: 8081 (via docker-compose)"
echo "   PID: $APP_PID"
echo "   Health: http://localhost:8080/health"
echo ""
echo "🔗 Service Architecture:"
echo "   Client → Host:8081 → Container:8080 (app_docker.py)"
echo "                              ↓ calls"
echo "                         Container:8081 (quantclaw_webhook.py)"
echo ""
echo "📋 Logs:"
echo "   tail -f /tmp/quantclaw_webhook.log"
echo "   tail -f /tmp/app_docker.log"
echo ""
echo "🛑 Stop Services:"
echo "   pkill -f 'quantclaw_webhook|app_docker'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
