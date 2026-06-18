#!/bin/bash
# 从宿主机启动 Docker 容器内的 QuantClaw 服务
# 使用方法: ./start_in_docker.sh

set -e

COMPOSE_DIR="/home/lh/work/Docker/openclaw-2026.5.18"
CONTAINER_NAME="openclaw-2026518-openclaw-gateway-1"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Starting QuantClaw Services in Docker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查 Gateway 容器是否运行
RUNNING=$(sudo docker ps --format '{{.Names}}' | grep "^${CONTAINER_NAME}$" || true)
if [ -z "$RUNNING" ]; then
    echo "⚠️  Gateway container is not running"
    echo ""

    # 检查容器是否存在（只是停止了）
    EXISTS=$(sudo docker ps -a --format '{{.Names}}' | grep "^${CONTAINER_NAME}$" || true)
    if [ -n "$EXISTS" ]; then
        echo "📦 Container exists but stopped, starting docker-compose services..."
        cd ${COMPOSE_DIR}
        sudo docker compose up -d

        # 等待容器启动和健康检查
        echo "⏳ Waiting for Gateway to be healthy..."
        for i in {1..30}; do
            if sudo docker ps --format '{{.Names}}\t{{.Status}}' | grep -q "^${CONTAINER_NAME}.*healthy"; then
                echo "✅ Gateway is healthy"
                break
            fi
            if [ $i -eq 30 ]; then
                echo "⚠️  Gateway health check timeout (but may still work)"
                break
            fi
            sleep 2
        done

        # 再次检查是否运行
        RUNNING2=$(sudo docker ps --format '{{.Names}}' | grep "^${CONTAINER_NAME}$" || true)
        if [ -z "$RUNNING2" ]; then
            echo "❌ Failed to start Gateway container"
            exit 1
        fi
        echo "✅ Docker Compose services started"
    else
        # 容器不存在
        echo "❌ Gateway container does not exist"
        echo ""
        echo "Create and start the containers first:"
        echo "  cd ${COMPOSE_DIR}"
        echo "  docker compose up -d"
        exit 1
    fi
else
    echo "✅ Gateway container is running: ${CONTAINER_NAME}"
fi

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
echo "   docker exec ${CONTAINER_NAME} tail -f /tmp/quantclaw_webhook.log"
echo "   docker exec ${CONTAINER_NAME} tail -f /tmp/app_docker.log"
echo ""
echo "🛑 Stop services:"
echo "   docker exec ${CONTAINER_NAME} bash /home/node/quantclaw/server/stop_docker.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"