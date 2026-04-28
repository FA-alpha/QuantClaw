# Token 验证配置

## 功能说明

在自动注册用户前，调用外部 API 验证 token 真实性，避免无效 token 创建账户。

## 配置方式

### 1. Gateway 配置文件

编辑 `~/.clawdbot/config.json`：

```json
{
  "plugins": {
    "entries": {
      "quantclaw-auth": {
        "config": {
          "tokenValidation": {
            "enabled": true,
            "apiUrl": "https://your-backend.com/Account/usage_info",
            "apiMethod": "POST",
            "showType": 2,
            "timeoutMs": 5000,
            "apiHeaders": {
              "User-Agent": "QuantClaw/1.0"
            }
          }
        }
      }
    }
  }
}
```

### 2. 环境变量（可选）

```bash
export QUANTCLAW_TOKEN_API="https://your-backend.com/Account/usage_info"
```

## API 接口规范

### 请求

```http
POST /Account/usage_info HTTP/1.1
Host: your-backend.com
Content-Type: application/json

{
  "show_type": 2,
  "token": "client-token-xxx"
}
```

### 响应

**成功（status=1）：**
```json
{
  "status": 1,
  "userId": "alice",
  "message": "Valid token"
}
```

**失败（status!=1）：**
```json
{
  "status": 0,
  "message": "Invalid or expired token"
}
```

## 验证逻辑

```
1. 客户端发送 {token, message}
   ↓
2. Webhook 接收请求
   ↓
3. 查找已绑定用户
   - 已有 → 直接返回
   - 新 token → 继续
   ↓
4. 调用外部 API 验证
   POST {show_type: 2, token}
   ↓
5. 检查 response.status
   - status === 1 → 通过验证
   - status !== 1 → 拒绝，返回错误
   ↓
6. 创建用户 + Agent
   ↓
7. 返回 sessionKey
```

## 错误处理

### 验证失败
```json
{
  "success": false,
  "error": "Invalid token"
}
```

### 网络超时
- 默认超时 5 秒
- 超时视为验证失败（可配置为跳过）

### API 不可用
- 记录错误日志
- 可配置降级策略（允许/拒绝）

## 向后兼容

如果 `tokenValidation.enabled = false` 或未配置 `apiUrl`，则跳过验证，保持原有行为。

## 测试

### 1. 测试有效 token
```bash
curl -X POST http://localhost:18789/webhook/quantclaw \
  -H "Content-Type: application/json" \
  -d '{
    "token": "valid-token-xxx",
    "message": "__auth_check__"
  }'
```

**预期：** `{"success": true, "userId": "u_xxx", ...}`

### 2. 测试无效 token
```bash
curl -X POST http://localhost:18789/webhook/quantclaw \
  -H "Content-Type: application/json" \
  -d '{
    "token": "invalid-token",
    "message": "__auth_check__"
  }'
```

**预期：** `{"success": false, "error": "Invalid token"}`

### 3. 查看日志
```bash
journalctl --user -u clawdbot-gateway -f | grep "quantclaw-auth"
```

## 前端集成

### JavaScript 错误处理

```javascript
const resp = await fetch('/api/auth', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({token})
});

const data = await resp.json();

if (!data.success) {
  if (data.error === 'Invalid token') {
    alert('Token 验证失败，请检查是否正确');
    // 清除本地 token
    localStorage.removeItem('quantclaw_token');
    showLoginPage();
  }
}
```

## 安全建议

1. **使用 HTTPS**  
   `apiUrl` 必须使用 `https://` 防止中间人攻击

2. **设置超时**  
   避免验证接口响应慢导致用户等待

3. **限流保护**  
   在验证 API 前端加限流，防止暴力破解

4. **日志监控**  
   记录验证失败次数，检测异常行为

## 常见问题

### Q: 验证接口返回非标准格式怎么办？

修改 `token-validator.ts` 中的 `validate()` 方法适配你的响应格式。

### Q: 如何临时禁用验证？

```bash
clawdbot config set plugins.entries.quantclaw-auth.config.tokenValidation.enabled false
clawdbot gateway restart
```

### Q: 验证失败但想强制通过？

使用 CLI 手动注册：
```bash
clawdbot quantclaw register user123
```

手动注册的用户会生成新 token，绕过验证。

## 配置示例

### 完整配置
```json
{
  "plugins": {
    "entries": {
      "quantclaw-auth": {
        "config": {
          "dataPath": "~/.quantclaw/users.json",
          "workspaceBase": "~/quantclaw-users",
          "defaultModel": "openrouter/anthropic/claude-sonnet-4-5",
          "webhookPath": "/webhook/quantclaw",
          "autoRegister": true,
          "skillsPath": "~/work/QuantClaw/skills",
          "templatePath": "~/work/QuantClaw/templates/agent-workspace",
          "tokenValidation": {
            "enabled": true,
            "apiUrl": "https://api.quantclaw.com/Account/usage_info",
            "apiMethod": "POST",
            "showType": 2,
            "timeoutMs": 5000
          }
        }
      }
    }
  }
}
```

### 最小配置（仅启用验证）
```json
{
  "plugins": {
    "entries": {
      "quantclaw-auth": {
        "config": {
          "tokenValidation": {
            "enabled": true,
            "apiUrl": "https://api.quantclaw.com/Account/usage_info"
          }
        }
      }
    }
  }
}
```
