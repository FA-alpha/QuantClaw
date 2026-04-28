#!/bin/bash
# 安全启用 Token 验证

set -e

CONFIG_FILE="$HOME/.clawdbot/clawdbot.json"
BACKUP_FILE="$HOME/.clawdbot/clawdbot.json.backup-$(date +%Y%m%d-%H%M%S)"

# 1. 备份
echo "📦 备份配置文件..."
cp "$CONFIG_FILE" "$BACKUP_FILE"
echo "   已备份到: $BACKUP_FILE"

# 2. 使用 jq 安全修改配置
echo "🔧 更新配置..."

if ! command -v jq &> /dev/null; then
    echo "⚠️  jq 未安装，正在安装..."
    sudo apt-get update && sudo apt-get install -y jq
fi

# 使用 jq 添加 token 验证配置
jq '.plugins.entries["quantclaw-auth"].config += {
  "autoRegister": true,
  "skillsPath": "/home/ubuntu/work/QuantClaw/skills",
  "templatePath": "/home/ubuntu/work/QuantClaw/templates/agent-workspace",
  "tokenValidation": {
    "enabled": true,
    "apiUrl": "https://www.fourieralpha.com/Mobile/Account/usage_info",
    "apiMethod": "POST",
    "showType": 2,
    "timeoutMs": 5000
  }
}' "$CONFIG_FILE" > "$CONFIG_FILE.tmp"

# 3. 验证 JSON 格式
echo "✅ 验证 JSON 格式..."
if python3 -m json.tool "$CONFIG_FILE.tmp" > /dev/null 2>&1; then
    mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    echo "✅ 配置已更新"
else
    echo "❌ JSON 格式错误，保持原配置"
    rm "$CONFIG_FILE.tmp"
    exit 1
fi

# 4. 显示差异
echo ""
echo "📊 配置变化:"
diff -u "$BACKUP_FILE" "$CONFIG_FILE" || true

echo ""
echo "✅ 完成！"
echo ""
echo "📝 下一步:"
echo "   1. 检查配置: cat $CONFIG_FILE | jq .plugins.entries.\"quantclaw-auth\".config.tokenValidation"
echo "   2. 重启 Gateway: clawdbot gateway restart"
echo "   3. 测试认证: curl -X POST http://localhost:8080/api/auth -H 'Content-Type: application/json' -d '{\"token\":\"your-token\"}'"
echo ""
echo "🔄 回退命令:"
echo "   cp $BACKUP_FILE $CONFIG_FILE"
echo "   clawdbot gateway restart"
