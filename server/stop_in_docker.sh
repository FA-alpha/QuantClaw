#!/bin/bash
# 从宿主机停止 Docker 容器内的 QuantClaw 服务

CONTAINER_NAME="openclaw-2026518-openclaw-gateway-1"

echo "🛑 Stopping QuantClaw Services in Docker..."

if ! sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Container ${CONTAINER_NAME} is not running"
    exit 1
fi

sudo docker exec ${CONTAINER_NAME} bash /home/node/quantclaw/server/stop_docker.sh

echo "✅ Services stopped"
