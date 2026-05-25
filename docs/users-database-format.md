# QuantClaw 用户数据库格式

## 📄 文件位置

**宿主机**: `/home/ubuntu/.openclaw/quantclaw-users.json`  
**容器内**: `/home/node/.openclaw/quantclaw-users.json`

---

## 📊 JSON 结构

```json
{
  "users": [
    {
      "userId": "user_abc123",
      "token": "abc123def456...",
      "agentId": "quantclaw-user-abc123",
      "workspace": "/home/node/quantclaw-users/user_abc123",
      "createdAt": "2026-05-20T08:30:00.000Z",
      "enabled": true
    },
    {
      "userId": "user_xyz789",
      "token": "xyz789uvw012...",
      "agentId": "quantclaw-user-xyz789",
      "workspace": "/home/node/quantclaw-users/user_xyz789",
      "createdAt": "2026-05-20T09:15:00.000Z",
      "enabled": true
    }
  ]
}
```

---

## 🔑 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `userId` | string | 用户唯一标识，格式：`user_<token前6位>` |
| `token` | string | 认证 token（32-64字符），用于 webhook 请求 |
| `agentId` | string | 关联的 Agent ID，格式：`quantclaw-user-<token前6位>` |
| `workspace` | string | 用户工作空间路径（容器内路径） |
| `createdAt` | string | 创建时间（ISO 8601 格式） |
| `enabled` | boolean | 是否启用（false 则拒绝请求） |

---

## 🔐 Token 认证流程

```
Webhook 请求
    ↓
Header: Authorization: Bearer <token>
    ↓
查找 quantclaw-users.json
    ↓
匹配 token
    ↓ (找到)
获取 agentId 和 workspace
    ↓
路由到对应 Agent
    ↓
过滤消息（keywords/llm）
    ↓
返回响应
```

---

## 📝 手动添加用户示例

```bash
# 1. 生成 token
TOKEN=$(openssl rand -hex 32)
USER_ID="user_${TOKEN:0:6}"

# 2. 创建工作空间
sudo docker exec openclaw-2026518-openclaw-gateway-1 \
  mkdir -p /home/node/quantclaw-users/${USER_ID}

# 3. 复制模板
sudo docker exec openclaw-2026518-openclaw-gateway-1 \
  cp -r /home/node/quantclaw/templates/agent-workspace/* \
  /home/node/quantclaw-users/${USER_ID}/

# 4. 编辑数据库（在宿主机）
# 添加用户记录到 /home/ubuntu/.openclaw/quantclaw-users.json
```

---

## ⚙️ 自动注册

当 `autoRegister: true` 时，首次使用 token 访问会自动：

1. 生成 `userId` 和 `agentId`
2. 创建工作空间目录
3. 复制模板文件
4. 写入数据库
5. 返回 Agent 响应

---

## 🔍 查询命令

```bash
# 查看用户数据库
cat /home/ubuntu/.openclaw/quantclaw-users.json | jq

# 统计用户数量
jq '.users | length' /home/ubuntu/.openclaw/quantclaw-users.json

# 查找特定用户
jq '.users[] | select(.userId=="user_abc123")' /home/ubuntu/.openclaw/quantclaw-users.json

# 列出所有 token
jq -r '.users[].token' /home/ubuntu/.openclaw/quantclaw-users.json
```

---

## ⚠️ 安全注意事项

1. **文件权限**: 确保只有 node 用户（UID 1000）可读写
   ```bash
   sudo chown 1000:1000 /home/ubuntu/.openclaw/quantclaw-users.json
   sudo chmod 600 /home/ubuntu/.openclaw/quantclaw-users.json
   ```

2. **Token 保护**: 不要在日志中输出完整 token
3. **备份**: 定期备份用户数据库
   ```bash
   cp /home/ubuntu/.openclaw/quantclaw-users.json \
      /home/ubuntu/.openclaw/quantclaw-users.json.backup-$(date +%s)
   ```

---

**最后更新**: 2026-05-20
