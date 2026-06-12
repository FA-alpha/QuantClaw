#!/bin/bash
# 从宿主机停止 Docker 容器内的 QuantClaw 服务

# Auto-detect the running gateway container
CONTAINER_NAME=$(docker ps --format '{{.Names}}' 2>/dev/null | grep 'openclaw.*gateway' | head -1)

echo "🛑 Stopping QuantClaw Services in Docker..."

if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Container ${CONTAINER_NAME} is not running"
    exit 1
fi

docker exec ${CONTAINER_NAME} bash /home/node/quantclaw/server/stop_docker.sh

echo "✅ Services stopped"