# QuantClaw 鉴权系统

## 概述

QuantClaw 采用 **CLI 管理 + Webhook 聊天** 模式：

- **管理员 CLI** → 注册用户、管理 Agent、配置凭证
- **Webhook API** → 外部系统发送聊天请求，路由到对应 Agent
- **消息过滤** → 只处理量化相关问题，拒绝无关闲聊

## 架构

```
┌─────────────────────────────────────────────────────┐
│                   外部系统                          │
│  (Web App / 小程序 / API Client)                   │
└─────────────────┬───────────────────────────────────┘
                  │ POST /webhook/quantclaw
                  │ { apiKey, message, sessionId }
                  ▼
┌─────────────────────────────────────────────────────┐
│              quantclaw-auth 插件                    │
│  1. 验证 API Key                                   │
│  2. 查找对应 Agent                                 │
│  3. 路由消息到 Agent Session                       │
│  4. 返回 Agent 回复                                │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│              用户独立 Agent                         │
│  qc-alice/  qc-bob/  qc-xxx/                       │
│  各自独立的 workspace + session                    │
└─────────────────────────────────────────────────────┘
```

## 安装

### 1. 安装插件

```bash
cd ~/work/QuantClaw
clawdbot plugins install -l ./extensions/quantclaw-auth
```

### 2. 配置插件

编辑 `~/.clawdbot/clawdbot.json`：

```json5
{
  plugins: {
    enabled: true,
    entries: {
      "quantclaw-auth": {
        enabled: true,
        config: {
          dataPath: "~/.quantclaw/users.yaml",
          workspaceBase: "~/quantclaw-users",
          defaultModel: "anthropic/claude-sonnet-4-5",
          sandboxMode: "all",
          webhookPath: "/webhook/quantclaw",
          webhookSecret: "your-secret-here"  // 可选
        }
      }
    }
  }
}
```

### 3. 重启 Gateway

```bash
clawdbot gateway restart
```

## 消息过滤

Webhook 会自动过滤与量化无关的消息，只处理以下主题：

- ✅ 加密货币/数字货币
- ✅ 量化交易/交易策略
- ✅ 市场行情/价格分析
- ✅ 链上数据/DeFi
- ✅ 宏观经济对加密市场的影响
- ✅ 风险管理/仓位管理
- ✅ 回测/策略优化

以下类型会被拒绝：

- ❌ 闲聊 (你好、天气、新闻等)
- ❌ 无关话题 (电影、游戏、美食、旅游等)
- ❌ 非量化编程问题

### 过滤模式

| 模式 | 说明 | 速度 | 准确度 |
|------|------|------|--------|
| `keywords` | 仅关键词匹配 | 最快 | 一般 |
| `llm` | 使用 LLM 分类 | 较慢 | 最高 |
| `hybrid` | 关键词优先，不确定时用 LLM | 平衡 | 较高 |

推荐使用 `hybrid` 模式（默认）。

### 测试过滤

```bash
# CLI 测试
clawdbot quantclaw test-filter "查询 BTC 价格"
# ✅ 通过 - 消息与量化相关

clawdbot quantclaw test-filter "今天天气怎么样"
# 🚫 拒绝 - 消息与量化交易无关
```

### 被拒绝的响应

```json
{
  "success": false,
  "rejected": true,
  "error": "该问题与量化交易无关，请咨询加密货币、交易策略、行情分析等相关问题"
}
```

## CLI 命令

### 用户管理

```bash
# 注册新用户
clawdbot quantclaw register <userId>
clawdbot quantclaw register alice --binance-key xxx --binance-secret xxx

# 列出所有用户
clawdbot quantclaw list

# 查看用户详情
clawdbot quantclaw info <userId>
clawdbot quantclaw info alice --show-key

# 删除用户
clawdbot quantclaw delete <userId>

# 启用/禁用用户
clawdbot quantclaw enable <userId>
clawdbot quantclaw disable <userId>
```

### 凭证管理

```bash
# 更新凭证
clawdbot quantclaw set-credentials <userId> --binance-key xxx --binance-secret xxx

# 重新生成 API Key
clawdbot quantclaw regen-key <userId>
```

### 配置管理

```bash
# 查看生成的 Agent 配置
clawdbot quantclaw config

# 查看 Webhook 信息
clawdbot quantclaw webhook
```

## 注册流程

```bash
# 1. 注册用户
$ clawdbot quantclaw register alice

✅ 用户注册成功

   用户ID:    alice
   API Key:   qc_a1b2c3d4e5f6...
   Agent ID:  qc-alice
   Workspace: /home/ubuntu/quantclaw-users/qc-alice

📄 Agent 配置已生成: ~/.quantclaw/agents-config.yaml

⚠️  请将配置合并到 ~/.clawdbot/clawdbot.json 后运行:
   clawdbot gateway restart

# 2. 查看生成的配置
$ clawdbot quantclaw config

# 3. 合并配置并重启
$ clawdbot gateway restart
```

## Webhook API

### 请求

```
POST /webhook/quantclaw
Content-Type: application/json
X-QuantClaw-Signature: <hmac-sha256>  (如果配置了 secret)

{
  "apiKey": "qc_xxxxx",
  "message": "查询 BTC 价格",
  "sessionId": "chat-001"  // 可选，用于多轮对话
}
```

### 响应

**成功：**
```json
{
  "success": true,
  "reply": "当前 BTC 价格是 $67,500...",
  "sessionId": "chat-001"
}
```

**失败：**
```json
{
  "success": false,
  "error": "Invalid API key"
}
```

### 示例代码

**cURL:**
```bash
curl -X POST http://localhost:3000/webhook/quantclaw \
  -H "Content-Type: application/json" \
  -d '{"apiKey":"qc_xxx","message":"查询 BTC 价格"}'
```

**Python:**
```python
import requests

response = requests.post(
    "http://localhost:3000/webhook/quantclaw",
    json={
        "apiKey": "qc_xxxxx",
        "message": "查询 BTC 价格",
        "sessionId": "user-123"
    }
)
print(response.json())
```

**JavaScript:**
```javascript
const response = await fetch('http://localhost:3000/webhook/quantclaw', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    apiKey: 'qc_xxxxx',
    message: '查询 BTC 价格',
    sessionId: 'user-123'
  })
});
const data = await response.json();
```

### 签名验证

如果配置了 `webhookSecret`，请求需要包含签名头：

```python
import hmac
import hashlib
import json

payload = {"apiKey": "qc_xxx", "message": "hello"}
secret = "your-secret"

signature = hmac.new(
    secret.encode(),
    json.dumps(payload).encode(),
    hashlib.sha256
).hexdigest()

headers = {
    "Content-Type": "application/json",
    "X-QuantClaw-Signature": signature
}
```

## 数据结构

### 用户数据库 (`~/.quantclaw/users.yaml`)

```yaml
users:
  - userId: alice
    apiKey: qc_a1b2c3d4e5f6...
    agentId: qc-alice
    workspace: /home/ubuntu/quantclaw-users/qc-alice
    createdAt: "2024-01-15T10:30:00Z"
    enabled: true
    credentials:
      binance:
        apiKey: xxx
        secret: xxx
```

### Agent 配置 (`~/.quantclaw/agents-config.yaml`)

```yaml
agents:
  list:
    - id: qc-alice
      name: QuantClaw - alice
      workspace: /home/ubuntu/quantclaw-users/qc-alice
      model: anthropic/claude-sonnet-4-5
      sandbox:
        mode: all
        scope: agent
```

## 目录结构

```
~/.quantclaw/
├── users.yaml           # 用户数据库
└── agents-config.yaml   # 生成的 Agent 配置

~/quantclaw-users/
├── qc-alice/
│   ├── AGENTS.md
│   ├── SOUL.md
│   ├── .credentials.yaml
│   ├── strategies/
│   ├── data/
│   ├── backtests/
│   └── analysis/
└── qc-bob/
    └── ...
```

## 配置选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `dataPath` | `~/.quantclaw/users.yaml` | 用户数据库 |
| `workspaceBase` | `~/quantclaw-users` | Workspace 目录 |
| `defaultModel` | `anthropic/claude-sonnet-4-5` | 默认模型 |
| `sandboxMode` | `all` | 沙箱模式 |
| `webhookPath` | `/webhook/quantclaw` | Webhook 路径 |
| `webhookSecret` | - | 签名密钥 |
| `filterMode` | `hybrid` | 消息过滤模式 |
| `filterModel` | `anthropic/claude-haiku` | LLM 分类使用的模型 |

## 错误码

| HTTP 状态 | 说明 |
|-----------|------|
| 200 | 成功 |
| 400 | 缺少参数 |
| 401 | API Key 无效或签名错误 |
| 403 | 用户已禁用 |
| 500 | 内部错误 |

## 故障排查

### 插件未加载

```bash
clawdbot plugins list
clawdbot plugins info quantclaw-auth
```

### Webhook 404

检查 Gateway 是否重启，以及 `webhookPath` 配置。

### Agent 未生效

```bash
# 1. 查看配置
clawdbot quantclaw config

# 2. 合并到主配置后重启
clawdbot gateway restart

# 3. 检查 Agent 列表
clawdbot agents list
```

### 签名验证失败

确保：
1. 请求体 JSON 序列化方式一致
2. 密钥匹配
3. Header 名称正确：`X-QuantClaw-Signature`
