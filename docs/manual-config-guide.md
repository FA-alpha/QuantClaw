# 手动配置 Token 验证

## 方法 1: 使用自动脚本（推荐）

```bash
cd /home/ubuntu/work/QuantClaw
./scripts/enable-token-validation.sh
```

**自动完成：**
- ✅ 备份配置文件
- ✅ 验证 JSON 格式
- ✅ 显示配置差异
- ✅ 提供回退命令

---

## 方法 2: 手动编辑（安全）

### 步骤 1: 备份配置

```bash
cp ~/.clawdbot/clawdbot.json ~/.clawdbot/clawdbot.json.backup-$(date +%Y%m%d-%H%M%S)
```

### 步骤 2: 编辑配置

打开配置文件：

```bash
nano ~/.clawdbot/clawdbot.json
```

找到 `"quantclaw-auth"` 部分：

```json
"quantclaw-auth": {
  "enabled": true,
  "config": {
    "dataPath": "/home/ubuntu/.quantclaw/users.json",
    "workspaceBase": "~/quantclaw-users",
    "defaultModel": "openrouter/anthropic/claude-sonnet-4-5",
    "webhookPath": "/webhook/quantclaw"
  }
}
```

**添加以下字段**（注意逗号）：

```json
"quantclaw-auth": {
  "enabled": true,
  "config": {
    "dataPath": "/home/ubuntu/.quantclaw/users.json",
    "workspaceBase": "~/quantclaw-users",
    "defaultModel": "openrouter/anthropic/claude-sonnet-4-5",
    "webhookPath": "/webhook/quantclaw",
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
  }
}
```

### 步骤 3: 验证 JSON 格式

```bash
python3 -m json.tool ~/.clawdbot/clawdbot.json > /dev/null && echo "✅ JSON 有效" || echo "❌ JSON 错误"
```

如果报错，恢复备份：

```bash
cp ~/.clawdbot/clawdbot.json.backup-YYYYMMDD-HHMMSS ~/.clawdbot/clawdbot.json
```

### 步骤 4: 重启 Gateway

```bash
# 停止
pkill -f clawdbot-gateway

# 等待 2 秒
sleep 2

# 启动（在后台会自动重启）
ps aux | grep clawdbot-gateway
```

或者使用 systemd：

```bash
systemctl --user restart clawdbot-gateway
```

---

## 方法 3: 使用 jq 命令（最安全）

### 安装 jq

```bash
sudo apt-get update && sudo apt-get install -y jq
```

### 一键更新配置

```bash
# 备份
cp ~/.clawdbot/clawdbot.json ~/.clawdbot/clawdbot.json.backup

# 更新
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
}' ~/.clawdbot/clawdbot.json > ~/.clawdbot/clawdbot.json.new

# 验证
python3 -m json.tool ~/.clawdbot/clawdbot.json.new > /dev/null && \
  mv ~/.clawdbot/clawdbot.json.new ~/.clawdbot/clawdbot.json && \
  echo "✅ 配置已更新" || \
  echo "❌ 更新失败"
```

---

## 测试验证

### 1. 查看配置

```bash
cat ~/.clawdbot/clawdbot.json | jq '.plugins.entries["quantclaw-auth"].config.tokenValidation'
```

**预期输出：**
```json
{
  "enabled": true,
  "apiUrl": "https://www.fourieralpha.com/Mobile/Account/usage_info",
  "apiMethod": "POST",
  "showType": 2,
  "timeoutMs": 5000
}
```

### 2. 测试无效 token

```bash
curl -X POST http://localhost:8080/api/auth \
  -H "Content-Type: application/json" \
  -d '{"token":"invalid-token-123","sessionId":"main"}'
```

**预期返回：**
```json
{
  "success": false,
  "error": "Token validation failed: empty user_type"
}
```

### 3. 测试有效 token（需要真实 token）

```bash
curl -X POST http://localhost:8080/api/auth \
  -H "Content-Type: application/json" \
  -d '{"token":"YOUR_REAL_TOKEN","sessionId":"main"}'
```

**预期返回：**
```json
{
  "success": true,
  "userId": "u_xxx",
  "agentId": "qc-xxx",
  "sessionKey": "agent:qc-xxx:main",
  "isNewUser": true
}
```

### 4. 查看日志

```bash
# Gateway 日志
journalctl --user -u clawdbot-gateway -f | grep "quantclaw-auth"

# Server 日志
tail -f /tmp/quantclaw-server.log
```

---

## 回退配置

### 恢复备份

```bash
# 列出备份文件
ls -lt ~/.clawdbot/clawdbot.json.backup*

# 恢复最新备份
cp ~/.clawdbot/clawdbot.json.backup-YYYYMMDD-HHMMSS ~/.clawdbot/clawdbot.json

# 重启 Gateway
pkill -f clawdbot-gateway
```

### 禁用验证（不删除配置）

```bash
jq '.plugins.entries["quantclaw-auth"].config.tokenValidation.enabled = false' \
  ~/.clawdbot/clawdbot.json > ~/.clawdbot/clawdbot.json.tmp && \
  mv ~/.clawdbot/clawdbot.json.tmp ~/.clawdbot/clawdbot.json
```

---

## 常见问题

### Q: JSON 格式错误怎么办？

1. 检查语法：
   ```bash
   python3 -m json.tool ~/.clawdbot/clawdbot.json
   ```

2. 常见错误：
   - 缺少逗号
   - 多余逗号（最后一个字段后）
   - 引号不匹配
   - 括号不匹配

3. 使用在线工具验证：https://jsonlint.com

### Q: Gateway 启动失败？

```bash
# 查看错误日志
journalctl --user -u clawdbot-gateway -n 50

# 检查配置
clawdbot config validate

# 恢复备份
cp ~/.clawdbot/clawdbot.json.backup ~/.clawdbot/clawdbot.json
```

### Q: 如何临时禁用验证？

编辑配置，将 `enabled` 改为 `false`：

```json
"tokenValidation": {
  "enabled": false,
  ...
}
```

### Q: 验证接口超时怎么办？

增加超时时间：

```json
"tokenValidation": {
  "timeoutMs": 10000
}
```

---

## 完整配置参考

见文件：`/home/ubuntu/work/QuantClaw/config-token-validation-full.json`

```bash
cat /home/ubuntu/work/QuantClaw/config-token-validation-full.json
```
