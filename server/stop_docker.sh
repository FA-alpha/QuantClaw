#!/bin/bash
# QuantClaw Docker 环境停止脚本

echo "🛑 Stopping QuantClaw Services..."

# 停止进程
pkill -f "quantclaw_webhook.py" && echo "  ✓ Stopped quantclaw_webhook" || echo "  ℹ  quantclaw_webhook not running"
pkill -f "app_docker.py" && echo "  ✓ Stopped app_docker" || echo "  ℹ  app_docker not running"

# 删除 PID 文件
rm -f /tmp/quantclaw_auth.pid /tmp/quantclaw_app.pid

echo "✅ Services stopped"
