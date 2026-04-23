# QuantClaw 架构说明

## 系统组件

```
┌─────────────────┐
│   前端 (Web)    │ 
│  localhost:8080 │
└────────┬────────┘
         │ HTTP/WebSocket
         ▼
┌─────────────────┐
│  Server (Py)    │  认证 + 聊天记录
│  server/app.py  │
└────────┬────────┘
         │ Webhook
         ▼
┌─────────────────┐
│ quantclaw-auth  │  用户管理 + Agent 注册
│ (Plugin/TS)     │
└────────┬────────┘
         │ API
         ▼
┌─────────────────┐
│ Clawdbot        │  Gateway + Agent 运行时
│ Gateway:18789   │
└─────────────────┘
```

---

## 认证流程

### 1. 首次访问（自动注册）

```
用户 → Server → quantclaw-auth → 创建用户 → 生成 workspace → 注册 Agent
```

**步骤**：
1. 用户使用 token 访问前端
2. Server 转发到 `/webhook/quantclaw`
3. Plugin 检查 token，如果不存在则：
   - 生成 userId（hash 前12位）
   - 创建 agentId: `qc-{hash}`
   - 创建 workspace: `~/quantclaw-users/qc-{hash}`
   - 从模板复制 MD 文件
   - **注册 Agent 到 Gateway**（关键）
4. 返回认证信息

### 2. Agent 注册问题（已修复）

**之前的问题**：
- Plugin 将 agent 写入 `~/.quantclaw/agents-config.json`
- Gateway 不读取这个文件
- Gateway 找不到 agent 时使用 fallback 模式
- 创建了错误的 workspace: `/home/ubuntu/clawd-qc-{hash}`

**解决方案**：
- 直接修改 Gateway 配置文件 `~/.clawdbot/clawdbot.json`
- 将 agent 添加到 `agents.list` 数组
- **需要重启 Gateway 生效**

**未来优化**：
- 如果 Clawdbot 提供动态注册 API，使用 API 而非修改配置文件

---

## 工作区结构

### 用户工作区
```
~/quantclaw-users/
├── qc-{hash}/                    # 用户 Agent 工作区
│   ├── AGENTS.md                 # 项目结构 (从模板)
│   ├── SOUL.md                   # Agent 个性 (从模板)
│   ├── IDENTITY.md               # 身份定义 (从模板)
│   ├── MEMORY.md                 # 记忆索引 (从模板)
│   ├── TOOLS.md                  # 工具笔记 (从模板)
│   ├── USER.md                   # 用户信息 (从模板)
│   ├── HEARTBEAT.md              # 定期任务 (从模板)
│   ├── skills/ -> ../../skills   # 软链接到技能目录
│   ├── strategies/               # 策略笔记
│   ├── data/                     # 数据文件
│   ├── backtests/                # 回测结果
│   └── analysis/                 # 分析报告
```

### 共享技能
```
~/work/QuantClaw/skills/
└── backtest-query/               # 回测查询技能
    ├── SKILL.md
    └── query.py
```

每个用户的 `skills/` 是指向这个目录的软链接。

---

## 配置文件

### Gateway 配置
`~/.clawdbot/clawdbot.json`

```json
{
  "agents": {
    "list": [
      {
        "id": "qc-{hash}",
        "name": "QuantClaw - u_{hash}",
        "workspace": "/home/ubuntu/quantclaw-users/qc-{hash}",
        "model": {
          "primary": "openrouter/anthropic/claude-sonnet-4-5"
        }
      }
    ]
  },
  "plugins": {
    "entries": {
      "quantclaw-auth": {
        "enabled": true,
        "config": {
          "dataPath": "/home/ubuntu/.quantclaw/users.json",
          "workspaceBase": "~/quantclaw-users",
          "templatePath": "~/work/QuantClaw/templates/agent-workspace"
        }
      }
    }
  }
}
```

### 用户数据
`~/.quantclaw/users.json`

```json
{
  "users": [
    {
      "userId": "u_{hash}",
      "token": "client_token",
      "agentId": "qc-{hash}",
      "workspace": "/home/ubuntu/quantclaw-users/qc-{hash}",
      "createdAt": "2026-04-23T...",
      "enabled": true
    }
  ]
}
```

---

## 数据流

### 查询回测数据

```
用户输入 → Server → Gateway → Agent (qc-{hash})
                                   │
                                   ▼
                            读取 AGENTS.md
                                   │
                                   ▼
                            选择 backtest-query 技能
                                   │
                                   ▼
                            执行 skills/backtest-query/query.py
                                   │
                                   ▼
                            API 请求 (fourieralpha.com)
                                   │
                                   ▼
                            返回结果 → 用户
```

---

## 部署检查清单

### 首次部署
- [ ] 创建模板目录: `templates/agent-workspace/*.md`
- [ ] 配置插件路径: `plugins.load.paths`
- [ ] 启用插件: `plugins.entries.quantclaw-auth.enabled = true`
- [ ] 启动 Server: `cd server && python3 app.py`
- [ ] 启动 Gateway: `clawdbot gateway start`

### 模板更新
- [ ] 修改模板: `templates/agent-workspace/*.md`
- [ ] 同步到现有用户: `python scripts/sync-templates.py`
- [ ] 重启 Gateway (如需要)

### 排查问题
- [ ] 检查 Server 日志: `tail -f /tmp/quantclaw-server.log`
- [ ] 检查 Gateway 状态: `clawdbot gateway status`
- [ ] 检查用户数据: `cat ~/.quantclaw/users.json`
- [ ] 检查工作区: `ls ~/quantclaw-users/`
- [ ] 检查错误工作区: `ls ~/clawd-qc-*` (不应存在)

---

## 常见问题

### Q: 创建了 `clawd-qc-*` 目录？
A: Agent 未正确注册到 Gateway。检查插件是否正确写入 `~/.clawdbot/clawdbot.json`，然后重启 Gateway。

### Q: Agent 不使用技能？
A: 检查 SOUL.md 中的"能力边界"，确保允许"使用技能查询数据"。

### Q: 模板更新后新用户没有生效？
A: 检查 `templatePath` 配置是否正确，默认为 `~/work/QuantClaw/templates/agent-workspace`。

### Q: 如何更新现有用户的模板？
A: 使用 `python scripts/sync-templates.py --files SOUL.md`
