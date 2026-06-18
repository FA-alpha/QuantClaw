#!/bin/bash
# 从宿主机停止 Docker 容器内的 QuantClaw 服务

echo "🛑 Stopping QuantClaw Services in Docker..."

# Auto-detect the running gateway container
CONTAINER_NAME=$(sudo docker ps --format '{{.Names}}' 2>/dev/null | grep 'openclaw.*gateway' | head -1)

if [ -z "$CONTAINER_NAME" ]; then
    echo "❌ No OpenClaw gateway container found"
    echo ""
    echo "Available containers:"
    sudo docker ps --format '  {{.Names}}' 2>/dev/null || echo "  (none or no permission)"
    exit 1
fi

echo "📦 Found container: $CONTAINER_NAME"

if ! sudo docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Container ${CONTAINER_NAME} is not running"
    exit 1
fi

sudo docker exec -u root ${CONTAINER_NAME} bash /home/node/quantclaw/server/stop_docker.sh

echo "✅ Services stopped"
