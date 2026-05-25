# QuantClaw Auth 插件配置状态

**更新时间**: 2026-05-20 08:30 UTC

---

## ✅ 已完成配置

### 1. Docker Volume 挂载 ✅

**文件**: `/home/ubuntu/work/Docker/openclaw-2026.5.18/docker-compose.yml`

```yaml
volumes:
  - /home/ubuntu/.openclaw:/home/node/.openclaw
  - /home/ubuntu/.openclaw/workspace:/home/node/.openclaw/workspace
  - /home/ubuntu/.openclaw-auth-profile-secrets:/home/node/.config/openclaw
  - /home/ubuntu/work/QuantClaw/extensions/quantclaw-auth:/home/node/.openclaw/npm/node_modules/quantclaw-auth:ro
  - /home/ubuntu/work/QuantClaw/skills:/home/node/quantclaw/skills:ro
  - /home/ubuntu/work/QuantClaw/templates:/home/node/quantclaw/templates:ro
  - /home/ubuntu/quantclaw-users:/home/node/quantclaw-users:rw
```

**验证**:
```bash
sudo docker exec openclaw-2026518-openclaw-gateway-1 ls -la /home/node/ | grep quantclaw
# 应该看到:
# drwxr-xr-x 4 root root quantclaw
# drwxrwxr-x 2 node node quantclaw-users
```

---

### 2. Openclaw 插件配置 ✅

**文件**: `/home/ubuntu/.openclaw/openclaw.json`

```json
{
  "plugins": {
    "entries": {
      "quantclaw-auth": {
        "enabled": true,
        "config": {
          "dataPath": "/home/node/.openclaw/quantclaw-users.json",
          "workspaceBase": "/home/node/quantclaw-users",
          "webhookPath": "/webhook/quantclaw",
          "filterMode": "keywords",
          "autoRegister": true,
          "skillsPath": "/home/node/quantclaw/skills",
          "templatePath": "/home/node/quantclaw/templates/agent-workspace"
        }
      }
    }
  }
}
```

---

### 3. 用户数据库初始化 ✅

**文件**: `/home/ubuntu/.openclaw/quantclaw-users.json`

```json
{
  "users": []
}
```

**权限**:
```
-rw------- 1 1000 1000 18 quantclaw-users.json
```

**验证**:
```bash
stat -c "UID: %u, GID: %g" /home/ubuntu/.openclaw/quantclaw-users.json
# 应该输出: UID: 1000, GID: 1000
```

---

### 4. 用户工作空间目录 ✅

**路径**: `/home/ubuntu/quantclaw-users/`

**权限**:
```bash
drwxrwxr-x 1000:1000 quantclaw-users/
```

**内容**: 空目录（用户注册后自动创建子目录）

---

### 5. 路径映射 ✅

| 功能 | 宿主机路径 | 容器内路径 | 权限 |
|------|-----------|-----------|------|
| 用户数据库 | `/home/ubuntu/.openclaw/quantclaw-users.json` | `/home/node/.openclaw/quantclaw-users.json` | RW |
| 用户工作空间 | `/home/ubuntu/quantclaw-users/` | `/home/node/quantclaw-users/` | RW |
| 技能库 | `/home/ubuntu/work/QuantClaw/skills/` | `/home/node/quantclaw/skills/` | RO |
| Agent 模板 | `/home/ubuntu/work/QuantClaw/templates/agent-workspace/` | `/home/node/quantclaw/templates/agent-workspace/` | RO |
| 插件源码 | `/home/ubuntu/work/QuantClaw/extensions/quantclaw-auth/` | `/home/node/.openclaw/npm/node_modules/quantclaw-auth/` | RO |

---

## ⚠️ 待完成

### 编译 TypeScript 插件 ❌

**当前状态**: 插件是 `.ts` 源码，Openclaw 无法加载

**需要执行**:

```bash
# 1. 安装依赖
cd /home/ubuntu/work/QuantClaw/extensions/quantclaw-auth
npm install --save-dev typescript @types/node

# 2. 编译
npx tsc

# 3. 修改 package.json
sed -i 's/"main": "index.ts"/"main": "dist\/index.js"/' package.json
sed -i 's/"extensions": \[".\/index.ts"\]/"extensions": [".\\/dist\\/index.js"]/' clawdbot.plugin.json

# 4. 重启容器
cd /home/ubuntu/work/Docker/openclaw-2026.5.18
sudo docker compose restart openclaw-gateway

# 5. 验证（等待30秒启动）
sleep 30
sudo docker logs openclaw-2026518-openclaw-gateway-1 2>&1 | grep "listening"
# 期望输出: http server listening (9 plugins: ..., quantclaw-auth, ...)
```

---

## 📋 验证清单

- [x] Docker volumes 挂载
- [x] 插件配置添加到 openclaw.json
- [x] 用户数据库文件创建 (JSON 格式)
- [x] 用户工作空间目录创建
- [x] 文件权限设置 (UID/GID 1000)
- [x] 路径修正为容器内路径
- [ ] TypeScript 编译
- [ ] 插件加载验证
- [ ] Webhook 端点测试

---

## 🧪 测试步骤（编译后）

### 1. 验证插件加载

```bash
sudo docker logs openclaw-2026518-openclaw-gateway-1 2>&1 | grep -i quantclaw
```

期望看到：
```
[quantclaw-auth] Loaded 0 users
[gateway] http server listening (9 plugins: ..., quantclaw-auth, ...)
```

### 2. 测试 Webhook 端点

```bash
# 生成测试 token
TOKEN=$(openssl rand -hex 32)
echo "测试 Token: $TOKEN"

# 发送请求（自动注册）
curl -X POST http://localhost:19789/webhook/quantclaw \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "查询 BTC 价格"}'
```

期望响应：
```json
{
  "ok": true,
  "response": "正在查询 BTC 价格...",
  "userId": "user_abc123"
}
```

### 3. 验证用户创建

```bash
# 查看数据库
cat /home/ubuntu/.openclaw/quantclaw-users.json | jq

# 查看工作空间
ls -la /home/ubuntu/quantclaw-users/
```

---

## 📚 相关文档

1. **[docker-plugin-integration.md](./docker-plugin-integration.md)** - 插件对接详细步骤
2. **[docker-path-mapping.md](./docker-path-mapping.md)** - 路径映射说明
3. **[users-database-format.md](./users-database-format.md)** - 用户数据库格式

---

## 🐛 故障排查

### 问题：插件未加载

**症状**: Gateway 日志只显示 8 个插件

**排查**:
```bash
# 1. 检查插件目录
sudo docker exec openclaw-2026518-openclaw-gateway-1 ls -la /home/node/.openclaw/npm/node_modules/quantclaw-auth/

# 2. 检查是否编译
sudo docker exec openclaw-2026518-openclaw-gateway-1 ls /home/node/.openclaw/npm/node_modules/quantclaw-auth/dist/

# 3. 查看完整日志
sudo docker logs openclaw-2026518-openclaw-gateway-1 2>&1 | grep -A5 -B5 plugin
```

### 问题：权限错误

**症状**: 日志显示 `EACCES: permission denied`

**解决**:
```bash
sudo chown -R 1000:1000 /home/ubuntu/quantclaw-users
sudo chmod 600 /home/ubuntu/.openclaw/quantclaw-users.json
```

---

**下一步**: 执行 TypeScript 编译并验证插件加载
