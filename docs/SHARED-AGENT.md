# 共享 Agent 方案

## 概述

所有用户共用一个 `quantclaw` agent，通过不同的 session 隔离对话上下文。

## 架构

```
用户A → Session: agent:quantclaw:u_abc123 → quantclaw agent
用户B → Session: agent:quantclaw:u_def456 → quantclaw agent  
用户C → Session: agent:quantclaw:u_xyz789 → quantclaw agent
```

## 优势

✅ **无需动态注册** - 不需要修改 Gateway 配置  
✅ **无需重启** - 新用户立即可用  
✅ **简化管理** - 只需维护一个 agent  
✅ **统一配置** - 所有用户使用相同的 SOUL.md/AGENTS.md

## 隔离机制

### 1. Session 隔离
每个用户使用独立的 sessionKey：
- 用户A: `agent:quantclaw:u_abc123`
- 用户B: `agent:quantclaw:u_def456`

Clawdbot 通过 sessionKey 隔离对话上下文和历史。

### 2. 数据隔离

**Server 层隔离**：
- 聊天记录存储：`server/data/chats/{userId}.json`
- 每个用户独立的聊天文件

**不隔离的部分**（共享）：
- Agent workspace: `/home/ubuntu/quantclaw/`
- 技能模块：`skills/backtest-query/`
- 配置文件：SOUL.md, AGENTS.md 等

## 配置

### Plugin 配置

```json
{
  "plugins": {
    "entries": {
      "quantclaw-auth": {
        "enabled": true,
        "config": {
          "sharedAgentId": "quantclaw",
          "dataPath": "/home/ubuntu/.quantclaw/users.json",
          "workspaceBase": "~/quantclaw-users"
        }
      }
    }
  }
}
```

- `sharedAgentId`: 共享的 agent ID（默认 `quantclaw`）
- 仍然会创建用户目录（用于将来扩展）

### Gateway 配置

只需定义一个 agent：

```json
{
  "agents": {
    "list": [
      {
        "id": "quantclaw",
        "name": "QuantClaw",
        "workspace": "/home/ubuntu/quantclaw",
        "model": {
          "primary": "openrouter/anthropic/claude-sonnet-4-5"
        }
      }
    ]
  }
}
```

## 工作流程

### 用户首次访问

```
1. 前端发送 token
2. quantclaw-auth 验证 token
3. 如果是新 token → 创建用户记录
   - userId: u_{hash}
   - 创建用户目录（预留）
4. 返回:
   - agentId: "quantclaw"  (共享)
   - sessionKey: "agent:quantclaw:{userId}"  (独立)
5. 前端连接 WebSocket
6. Gateway 路由到 quantclaw agent 的 {userId} session
```

## 限制与权衡

### ❌ 不隔离的内容

- **Agent 配置**：所有用户共享 SOUL.md, AGENTS.md
- **技能模块**：共享 skills/ 目录
- **文件系统**：共享 agent workspace

### ✅ 隔离的内容

- **对话上下文**：每个 session 独立
- **聊天历史**：Server 层独立存储
- **用户认证**：独立的 token 和 userId

### 适用场景

✅ **适合**：
- 所有用户使用相同功能
- 不需要用户级的个性化配置
- 只需隔离对话历史

❌ **不适合**：
- 需要用户级配置（如不同的 SOUL.md）
- 需要独立的文件工作区
- 需要用户级的技能定制

## 将来扩展

如果需要用户级隔离，可以：

1. **用户工作区**：在 agent 中检测 sessionKey，动态切换工作目录
2. **用户配置**：在 SOUL.md 中加入用户检测逻辑
3. **混合模式**：普通用户共享 agent，VIP 用户独立 agent

## 对比：独立 Agent 方案

| 特性 | 共享 Agent | 独立 Agent |
|------|-----------|-----------|
| 动态注册 | ❌ 不需要 | ✅ 需要 |
| 重启 Gateway | ❌ 不需要 | ✅ 需要 |
| 配置隔离 | ❌ 共享 | ✅ 独立 |
| 工作区隔离 | ❌ 共享 | ✅ 独立 |
| 对话隔离 | ✅ Session | ✅ Agent |
| 管理复杂度 | ✅ 低 | ❌ 高 |

## 结论

**共享 Agent 方案**更适合 QuantClaw 的场景：
- 所有用户功能相同
- 只需隔离对话和聊天历史
- 避免动态注册的复杂性
- 简化运维管理

如果将来需要用户级个性化，可以在此基础上扩展。
