# Webhook 迁移方案：从 TypeScript Extension 到 Python Webhook

## 📋 目标

将 `extensions/quantclaw-auth/index.ts` 改造为类似 `lark_webhook.py` 的独立 Python 服务，保留所有核心功能。

---

## 🔄 架构对比

### 当前架构（TypeScript Extension）
```
Client → Gateway HTTP API (/webhook/quantclaw)
    ↓
Gateway 加载 quantclaw-auth extension
    ↓
Extension 验证 token → 查找/创建 user
    ↓
Extension 调用 chat.send RPC → Agent session
    ↓
Gateway 返回响应 → Client
```

### 新架构（Python Webhook）
```
Client → Python Webhook Server (独立进程)
    ↓
验证 token → 查找/创建 user
    ↓
调用 clawdbot CLI: clawdbot agent --to qc-{userId}
    ↓
返回响应 → Client
```

---

## 🎯 保留功能

### 1. Token 验证
- ✅ 调用外部 API 验证 token
- ✅ 缓存验证结果
- ✅ 超时控制

### 2. 用户管理
- ✅ 自动注册（首次访问创建 user）
- ✅ token 绑定（每个 token 对应一个 user）
- ✅ 用户数据持久化（JSON 文件）
- ✅ 启用/禁用用户

### 3. Workspace 管理
- ✅ 自动创建用户 workspace
- ✅ 复制模板文件（AGENTS.md, SOUL.md 等）
- ✅ 软链接 skills 目录
- ✅ 初始化 memory 目录

### 4. 消息过滤
- ✅ 关键词过滤（可配置）
- ✅ 量化相关内容检测

---

## 🔧 实现细节

### 文件结构
```
/home/ubuntu/work/QuantClaw/
├── server/
│   ├── app.py              # 现有的 HTTP + WebSocket 服务
│   └── quantclaw_webhook.py  # 新的认证 Webhook 服务
├── templates/
│   └── agent-workspace/    # Workspace 模板
│       ├── AGENTS.md
│       ├── SOUL.md
│       ├── IDENTITY.md
│       └── ...
└── skills/                 # 量化技能模块
```

### 配置文件
```json
// ~/.quantclaw/webhook-config.json
{
  "port": 18861,
  "dataPath": "~/.quantclaw/users.json",
  "workspaceBase": "~/clawd-users",
  "defaultModel": "openrouter/anthropic/claude-sonnet-4-5",
  "skillsPath": "~/work/QuantClaw/skills",
  "templatePath": "~/work/QuantClaw/templates/agent-workspace",
  "tokenValidation": {
    "enabled": true,
    "apiUrl": "https://www.fourieralpha.com/Mobile/Account/usage_info",
    "apiMethod": "POST",
    "showType": 2,
    "timeoutMs": 5000
  },
  "filterMode": "off",
  "autoRegister": true
}
```

---

## 📝 关键差异

| 功能 | TypeScript Extension | Python Webhook |
|------|---------------------|----------------|
| **运行方式** | Gateway 加载 | 独立进程 |
| **消息发送** | chat.send RPC | clawdbot CLI |
| **上下文管理** | Gateway session | 自行构建 |
| **依赖** | Gateway 内部 | 独立 Python 环境 |
| **重启** | 需重启 Gateway | 独立重启 |
| **日志** | Gateway 日志 | 独立日志 |

---

## 🚀 迁移步骤

### 1. 创建 Python Webhook 服务
- 实现 HTTP 服务器（aiohttp）
- 实现 token 验证逻辑
- 实现用户管理
- 实现 workspace 创建

### 2. 调用方式改为 CLI
```python
# 旧方式（Extension）
await api.chat.send({
  sessionKey: `agent:${user.agentId}:main`,
  message: full_message
})

# 新方式（CLI）
subprocess.run([
  'clawdbot', 'agent',
  '--to', f'qc-{user.userId}',
  '--message', full_message,
  '--json'
])
```

### 3. 配置 SystemD 服务
```ini
[Unit]
Description=QuantClaw Webhook Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/work/QuantClaw/server
ExecStart=/usr/bin/python3 /home/ubuntu/work/QuantClaw/server/quantclaw_webhook.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## ⚠️ 注意事项

### 优点
- ✅ 独立部署，不依赖 Gateway
- ✅ 更灵活的上下文管理
- ✅ 可以实现语义检索（类似 lark_memory）
- ✅ 更好的性能控制

### 缺点
- ❌ 需要额外维护一个服务
- ❌ 不能直接使用 Gateway RPC
- ❌ 需要手动构建上下文

### 兼容性
- 前端代码**不需要修改**（API 路径和格式保持一致）
- 可以保留原 Extension 作为备份
- 平滑迁移，无需停服

---

## 📊 性能对比

| 指标 | Extension | Webhook |
|------|-----------|---------|
| 启动时间 | 随 Gateway | < 1s |
| 响应延迟 | +0ms | +10ms (CLI) |
| 并发处理 | Gateway 限制 | 独立控制 |
| 上下文构建 | 自动 | 手动 |
| 记忆系统 | Session 文件 | 可自定义 |

---

## 🎯 最终目标

创建一个功能完整的 `quantclaw_webhook.py`：
- 保留所有认证和用户管理功能
- 使用 `--to` 参数调用 Clawdbot
- 支持自定义上下文（可选添加语义检索）
- 独立运行，易于维护

---

*设计时间：2026-05-21*
