#!/bin/bash
# 从宿主机启动 Docker 容器内的 QuantClaw 服务
# 使用方法: ./start_in_docker.sh

set -e

COMPOSE_DIR="/home/ubuntu/work/Docker/openclaw-2026.5.18"
CONTAINER_NAME="openclaw-2026518-openclaw-gateway-1"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Starting QuantClaw Services in Docker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查容器是否运行
if ! sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Container ${CONTAINER_NAME} is not running"
    echo ""
    echo "Start the container first:"
    echo "  cd ${COMPOSE_DIR}"
    echo "  sudo docker compose up -d"
    exit 1
fi

echo "✅ Container is running: ${CONTAINER_NAME}"

# 在容器内执行启动脚本（使用 root 权限安装依赖）
echo ""
echo "📦 Executing start script inside container..."
sudo docker exec -u root ${CONTAINER_NAME} bash /home/node/quantclaw/server/start_docker.sh

# 显示状态
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Services Started!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔗 Access from host:"
echo "   http://localhost:8081 → Main Service (app_docker.py)"
echo ""
echo "📋 View logs:"
echo "   sudo docker exec ${CONTAINER_NAME} tail -f /tmp/quantclaw_webhook.log"
echo "   sudo docker exec ${CONTAINER_NAME} tail -f /tmp/app_docker.log"
echo ""
echo "🛑 Stop services:"
echo "   sudo docker exec ${CONTAINER_NAME} bash /home/node/quantclaw/server/stop_docker.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
