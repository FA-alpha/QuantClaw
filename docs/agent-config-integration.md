# Agent 配置集成说明

## 🔧 配置文件位置

### Docker Openclaw
- **主配置**: `/home/ubuntu/.openclaw/openclaw.json`
- **容器内路径**: `/home/node/.openclaw/openclaw.json`

---

## 📋 配置结构

### 修改前（错误）

插件写入自己的配置文件 `~/.quantclaw/agents-config.json`，Openclaw 无法发现这些 Agent。

### 修改后（正确）

插件直接更新 Openclaw 主配置文件的 `agents.list`：

```json
{
  "agents": {
    "defaults": {
      "workspace": "/home/node/.openclaw/workspace",
      "model": {
        "primary": "openrouter/deepseek/deepseek-v4-pro"
      }
    },
    "list": [
      {
        "id": "qc-abc123def456",
        "name": "QuantClaw - u_abc123def456",
        "workspace": "/home/node/quantclaw-users/u_abc123def456",
        "model": {
          "primary": "openrouter/deepseek/deepseek-v3.2"
        }
      }
    ]
  }
}
```

---

## 🔄 工作流程

```
用户首次请求
    ↓
autoRegister(clientToken)
    ↓
创建用户记录
    ↓
创建工作空间: /home/node/quantclaw-users/u_<hash>/
    ↓
调用 updateAgentConfig()
    ↓
读取 openclaw.json
    ↓
添加到 agents.list
    ↓
写回 openclaw.json
    ↓
Openclaw 自动发现新 Agent
```

---

## ✅ 验证

### 1. 检查配置文件

```bash
cat /home/ubuntu/.openclaw/openclaw.json | jq '.agents.list'
```

期望看到动态添加的 Agent。

### 2. 在容器内验证

```bash
sudo docker exec openclaw-2026518-openclaw-gateway-1 \
  cat /home/node/.openclaw/openclaw.json | grep -A10 '"list"'
```

### 3. 检查 Agent 目录

Openclaw 会在 `/home/node/.openclaw/agents/` 下创建子目录：

```bash
sudo docker exec openclaw-2026518-openclaw-gateway-1 \
  ls -la /home/node/.openclaw/agents/
```

应该看到：
```
drwxr-xr-x main/
drwxr-xr-x qc-abc123def456/
drwxr-xr-x qc-def456ghi789/
```

---

## 🎯 关键点

### 1. 配置路径
- ✅ 使用 `~/.openclaw/openclaw.json`（Openclaw 主配置）
- ❌ 不要用 `~/.quantclaw/agents-config.json`（插件私有配置）

### 2. model 字段格式
- ✅ `model: { primary: "openrouter/..." }`（对象格式）
- ❌ `model: "openrouter/..."`（字符串格式，旧版本）

### 3. workspace 路径
- ✅ 使用容器内路径：`/home/node/quantclaw-users/u_xxx/`
- ❌ 不要用宿主机路径：`/home/ubuntu/...`

---

## 🆚 对比：宿主机 vs Docker

### 宿主机 Clawdbot

**配置文件**: `/home/ubuntu/.clawdbot/clawdbot.json`

```json
{
  "agents": {
    "list": [
      {
        "id": "quantclaw",
        "workspace": "/home/ubuntu/quantclaw"
      },
      {
        "id": "qc-1801b7ff6f34",
        "workspace": "/home/ubuntu/clawd-qc-1801b7ff6f34"
      }
    ]
  }
}
```

### Docker Openclaw

**配置文件**: `/home/ubuntu/.openclaw/openclaw.json`

```json
{
  "agents": {
    "list": [
      {
        "id": "qc-abc123def456",
        "workspace": "/home/node/quantclaw-users/u_abc123def456"
      }
    ]
  }
}
```

**关键区别**：
- 路径前缀不同（`/home/ubuntu/` vs `/home/node/`）
- Docker 使用统一的 `quantclaw-users/` 目录

---

## 🔗 相关配置

### Volume 挂载

确保工作空间目录已挂载：

```yaml
volumes:
  - /home/ubuntu/quantclaw-users:/home/node/quantclaw-users:rw
```

### 插件配置

```json
{
  "plugins": {
    "entries": {
      "quantclaw-auth": {
        "config": {
          "workspaceBase": "/home/node/quantclaw-users",
          "defaultModel": "openrouter/deepseek/deepseek-v3.2"
        }
      }
    }
  }
}
```

---

## 📊 完整示例

**初始状态** - `openclaw.json`:
```json
{
  "agents": {
    "defaults": { "workspace": "/home/node/.openclaw/workspace" },
    "list": []
  }
}
```

**用户注册后** - `openclaw.json`:
```json
{
  "agents": {
    "defaults": { "workspace": "/home/node/.openclaw/workspace" },
    "list": [
      {
        "id": "qc-abc123def456",
        "name": "QuantClaw - u_abc123def456",
        "workspace": "/home/node/quantclaw-users/u_abc123def456",
        "model": { "primary": "openrouter/deepseek/deepseek-v3.2" }
      }
    ]
  }
}
```

**文件系统**:
```
/home/ubuntu/quantclaw-users/
└── u_abc123def456/
    ├── AGENTS.md
    ├── SOUL.md
    ├── MEMORY.md
    └── memory/

/home/ubuntu/.openclaw/agents/
└── qc-abc123def456/
    ├── agent/
    │   └── auth-profiles.json
    └── sessions/
        └── sessions.json
```

---

## 🐛 故障排查

### 问题：Agent 未被发现

**症状**: 配置文件有记录，但无法路由到 Agent

**排查**:
```bash
# 1. 检查配置格式
cat /home/ubuntu/.openclaw/openclaw.json | jq '.agents.list[]'

# 2. 检查工作空间是否存在
sudo docker exec openclaw-2026518-openclaw-gateway-1 \
  ls -la /home/node/quantclaw-users/

# 3. 重启 Gateway
cd /home/ubuntu/work/Docker/openclaw-2026.5.18
sudo docker compose restart openclaw-gateway
```

### 问题：配置文件被覆盖

**症状**: 手动添加的配置消失

**原因**: 插件写入时可能覆盖整个文件

**解决**: 使用插件的 `updateAgentConfig` 方法（已修复）

---

**Git commits**:
- `ee7368c` - 使用 workspaceBase 配置
- `26e760d` - 更新 openclaw.json 而非独立配置

**最后更新**: 2026-05-20
