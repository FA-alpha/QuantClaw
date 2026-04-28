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
   - 创建 workspace: `~/clawd-qc-{hash}`（直接在最外层）
   - 从模板复制 MD 文件
   - **注册 Agent 到 Gateway**（关键）
4. 返回认证信息

### 2. Agent 动态创建

**工作原理**：
- Gateway 不预先注册用户 agent（不写入配置文件）
- 当收到请求时，Gateway 自动创建 agent 实例（fallback 模式）
- workspace 路径由 `quantclaw-auth` 插件在用户数据中指定
- Agent 使用 `~/clawd-qc-{hash}` 作为工作区（直接在最外层）

**注意事项**：
- 用户数据必须包含正确的 `workspace` 路径
- 模板文件需要提前准备好
- Agent 配置继承 Gateway 的 `agents.defaults`

---

## 工作区结构

### 用户工作区
每个用户独立在最外层：
```
~/clawd-qc-{hash}/                # 用户 Agent 工作区（直接在最外层）
├── AGENTS.md                     # 项目结构 (从模板)
├── SOUL.md                       # Agent 个性 (从模板)
├── IDENTITY.md                   # 身份定义 (从模板)
├── MEMORY.md                     # 记忆索引 (从模板)
├── TOOLS.md                      # 工具笔记 (从模板)
├── USER.md                       # 用户信息 (从模板)
├── HEARTBEAT.md                  # 定期任务 (从模板)
├── skills/ -> work/QuantClaw/skills/  # 软链接到技能目录
├── strategies/                   # 策略笔记
├── data/                         # 数据文件
├── backtests/                    # 回测结果
└── analysis/                     # 分析报告
```

示例：
```
/home/ubuntu/
├── clawd-qc-a1b2c3d4e5f6/       # 用户1的工作区
├── clawd-qc-f6e5d4c3b2a1/       # 用户2的工作区
└── work/QuantClaw/              # 项目工程
    └── skills/                   # 共享技能目录
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
        "workspace": "/home/ubuntu/clawd-qc-{hash}",
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
          "workspacePrefix": "clawd-qc-",
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
      "workspace": "~/clawd-qc-{hash}",
      "createdAt": "2026-04-23T...",
      "enabled": true
    }
  ]
}
```

**关键字段**：
- `workspace`: 使用 `~` 开头的相对路径（会被 Gateway 展开）
- 格式：`~/clawd-qc-{hash}`（直接在最外层，便于管理和隔离）

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
- [ ] 验证模板文件: `ls ~/work/QuantClaw/templates/agent-workspace/`

---

## 常见问题

### Q: workspace 路径错误？
A: 确保 `users.json` 中的 `workspace` 字段使用 `~/clawd-qc-{hash}` 格式（`~` 开头，直接在最外层）。插件在创建用户时应该正确设置此路径。

### Q: Agent 不使用技能？
A: 检查以下内容：
1. 技能软链接是否存在: `ls -la ~/clawd-qc-{hash}/skills`
2. AGENTS.md 是否正确加载
3. Gateway 日志中是否有技能相关错误

### Q: 模板更新后新用户没有生效？
A: 检查 plugin 配置中的 `templatePath`，应为 `~/work/QuantClaw/templates/agent-workspace`。

### Q: 如何删除所有用户？
A: 清空三个位置的数据，然后重启 Gateway：
```bash
# 1. 用户注册信息
echo '{"users":[]}' > ~/.quantclaw/users.json
# 2. 工作区（删除所有 clawd-qc-* 目录）
rm -rf ~/clawd-qc-*
# 3. 聊天记录
rm -f ~/work/QuantClaw/server/data/chats/*.json
# 4. 重启 Gateway（清理 agent 实例缓存）
clawdbot gateway restart
```
