# Docker 容器路径映射说明

## 📂 路径映射表

| 宿主机路径 | 容器内路径 | 权限 | 说明 |
|-----------|-----------|------|------|
| `/home/ubuntu/.openclaw` | `/home/node/.openclaw` | RW | Openclaw 配置和状态 |
| `/home/ubuntu/.openclaw/workspace` | `/home/node/.openclaw/workspace` | RW | 默认工作空间 |
| `/home/ubuntu/.openclaw-auth-profile-secrets` | `/home/node/.config/openclaw` | RW | 认证配置 |
| `/home/ubuntu/work/QuantClaw/extensions/quantclaw-auth` | `/home/node/.openclaw/npm/node_modules/quantclaw-auth` | RO | 认证插件源码 |
| `/home/ubuntu/work/QuantClaw/skills` | `/home/node/quantclaw/skills` | RO | QuantClaw 技能库 |
| `/home/ubuntu/work/QuantClaw/templates` | `/home/node/quantclaw/templates` | RO | Agent 模板 |
| `/home/ubuntu/quantclaw-users` | `/home/node/quantclaw-users` | RW | **用户工作空间目录** |

---

## ⚙️ 插件配置路径

**配置文件位置：** `/home/ubuntu/.openclaw/openclaw.json`

```json
{
  "plugins": {
    "entries": {
      "quantclaw-auth": {
        "enabled": true,
        "config": {
          "dataPath": "/home/node/.openclaw/quantclaw-users.yaml",
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

## 📝 路径说明

### 1. 用户数据库文件
- **宿主机**: `/home/ubuntu/.openclaw/quantclaw-users.yaml`
- **容器内**: `/home/node/.openclaw/quantclaw-users.yaml`
- **自动创建**: 插件首次运行时创建
- **存储内容**: 用户 token、Agent ID、workspace 路径

### 2. 用户工作空间
- **宿主机**: `/home/ubuntu/quantclaw-users/`
- **容器内**: `/home/node/quantclaw-users/`
- **目录结构**:
  ```
  quantclaw-users/
  ├── user_abc123/          # 用户 token 前6位
  │   ├── AGENTS.md
  │   ├── SOUL.md
  │   ├── MEMORY.md
  │   └── memory/
  └── user_def456/
      └── ...
  ```

### 3. 技能库（只读）
- **宿主机**: `/home/ubuntu/work/QuantClaw/skills/`
- **容器内**: `/home/node/quantclaw/skills/`
- **子目录**:
  - `backtest-query/` - 回测查询
  - `start-backtest/` - 启动回测
  - `market-data/` - 市场数据
  - `strategies/` - 策略分析
  - 等等...

### 4. Agent 模板（只读）
- **宿主机**: `/home/ubuntu/work/QuantClaw/templates/agent-workspace/`
- **容器内**: `/home/node/quantclaw/templates/agent-workspace/`
- **内容**: AGENTS.md, SOUL.md, MEMORY.md 等模板文件
- **用途**: 新用户注册时复制到用户工作空间

---

## ⚠️ 注意事项

### 权限问题
- **容器内用户**: `node` (UID 1000, GID 1000)
- **宿主机目录所有者**: 需要与容器用户匹配
  ```bash
  sudo chown -R 1000:1000 /home/ubuntu/quantclaw-users
  ```

### 路径一致性
- ❌ **错误**: 在配置中使用宿主机路径（如 `/home/ubuntu/work/...`）
- ✅ **正确**: 使用容器内路径（如 `/home/node/quantclaw/...`）

### 文件创建
插件会自动创建：
1. `/home/node/.openclaw/quantclaw-users.yaml` - 用户数据库
2. `/home/node/quantclaw-users/<user_id>/` - 用户工作空间
3. 用户工作空间内的配置文件（从模板复制）

---

## 🔍 验证命令

```bash
# 检查挂载点
sudo docker exec openclaw-2026518-openclaw-gateway-1 ls -la /home/node/

# 验证 skills 可读
sudo docker exec openclaw-2026518-openclaw-gateway-1 ls /home/node/quantclaw/skills/

# 验证 templates 可读
sudo docker exec openclaw-2026518-openclaw-gateway-1 ls /home/node/quantclaw/templates/agent-workspace/

# 验证用户工作空间可写
sudo docker exec openclaw-2026518-openclaw-gateway-1 test -w /home/node/quantclaw-users && echo "✅ 可写" || echo "❌ 只读"

# 查看所有挂载
sudo docker inspect openclaw-2026518-openclaw-gateway-1 --format '{{range .Mounts}}{{.Source}} -> {{.Destination}} ({{.Mode}}){{"\n"}}{{end}}'
```

---

## 🐛 故障排查

### 问题1: 插件无法创建文件
**症状**: 日志显示 `EACCES: permission denied`

**解决**:
```bash
# 检查宿主机目录权限
ls -la /home/ubuntu/quantclaw-users

# 修正所有者
sudo chown -R 1000:1000 /home/ubuntu/quantclaw-users
```

### 问题2: 无法读取 skills
**症状**: 日志显示 `ENOENT: no such file or directory`

**解决**:
```bash
# 检查容器内路径
sudo docker exec openclaw-2026518-openclaw-gateway-1 ls /home/node/quantclaw/skills/

# 如果不存在，重新创建容器
cd /home/ubuntu/work/Docker/openclaw-2026.5.18
sudo docker compose down && sudo docker compose up -d
```

### 问题3: 配置路径错误
**症状**: 插件加载失败，日志无报错

**检查**:
```bash
# 查看配置
cat /home/ubuntu/.openclaw/openclaw.json | grep -A10 quantclaw-auth

# 确保所有 *Path 字段使用容器内路径（/home/node/...）
# 而不是宿主机路径（/home/ubuntu/...）
```

---

## 📊 路径使用流程

```
用户请求 (webhook)
    ↓
quantclaw-auth 插件
    ↓
检查 /home/node/.openclaw/quantclaw-users.yaml
    ↓ (不存在)
自动注册: 创建新 Agent
    ↓
复制模板: /home/node/quantclaw/templates/agent-workspace/
    ↓
创建工作空间: /home/node/quantclaw-users/<user_id>/
    ↓
写入数据库: quantclaw-users.yaml
    ↓
返回 Agent 信息
```

---

**最后更新**: 2026-05-20  
**Docker Compose 版本**: openclaw-2026.5.18
