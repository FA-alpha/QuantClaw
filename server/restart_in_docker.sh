#!/bin/bash
# 从宿主机重启 Docker 容器内的 QuantClaw 服务

set -e

CONTAINER_NAME="openclaw-gateway"

echo "🔄 Restarting QuantClaw Services in Docker..."

# 检查容器是否运行
if ! docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Container '$CONTAINER_NAME' not found or not running"
    echo "   Available containers:"
    docker ps --format "  - {{.Names}}"
    exit 1
fi

echo "✅ Container found: $CONTAINER_NAME"

# 停止旧进程（需要 root）
echo "🛑 Stopping old processes..."
docker exec -u root "$CONTAINER_NAME" pkill -f "quantclaw_webhook.py" 2>/dev/null || true
docker exec -u root "$CONTAINER_NAME" pkill -f "app_docker.py" 2>/dev/null || true
sleep 2

# 启动新进程
echo "🚀 Starting services..."
docker exec -d "$CONTAINER_NAME" bash -c "cd /home/lh/work/QuantClaw/server && ./start_docker.sh"

# 等待启动
sleep 5

# 检查健康状态
echo "🔍 Checking health..."
if docker exec "$CONTAINER_NAME" curl -sf http://localhost:8081/health > /dev/null 2>&1; then
    echo "✅ Auth service (8081) healthy"
else
    echo "❌ Auth service health check failed"
fi

if docker exec "$CONTAINER_NAME" curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ Main service (8080) healthy"
else
    echo "❌ Main service health check failed"
fi

echo ""
echo "📋 View logs:"
echo "   docker exec $CONTAINER_NAME tail -f /tmp/quantclaw_webhook.log"
echo "   docker exec $CONTAINER_NAME tail -f /tmp/app_docker.log"

echo ""
echo "✅ Restart complete!"
