# QuantClaw 部署指南

快速在新服务器上部署 QuantClaw 认证 + 聊天服务。

## 前置条件

- Ubuntu 22.04+ 或类似 Linux 系统
- Node.js 18+
- Python 3.10+
- Clawdbot 已安装并运行

## 目录结构

```
QuantClaw/
├── extensions/
│   └── quantclaw-auth/     # Clawdbot 认证插件
│       ├── index.ts
│       ├── package.json
│       └── clawdbot.plugin.json
├── server/                 # Python 聊天服务
│   ├── app.py
│   ├── requirements.txt
│   └── static/
└── skills/                 # 量化技能包
```

## 部署步骤

### 1. 克隆代码

```bash
# 选择你喜欢的目录
git clone https://github.com/FA-alpha/QuantClaw.git
cd QuantClaw
```

### 2. 安装 quantclaw-auth 插件

```bash
cd extensions/quantclaw-auth
npm install
cd ../..
```

### 3. 配置 Clawdbot

编辑 `~/.clawdbot/clawdbot.json`，添加插件配置：

```json
{
  "plugins": {
    "entries": {
      "quantclaw-auth": {
        "enabled": true,
        "config": {
          "dataPath": "~/.quantclaw/users.json",
          "workspaceBase": "~/quantclaw-users",
          "defaultModel": "openrouter/anthropic/claude-sonnet-4-5",
          "webhookPath": "/webhook/quantclaw"
        }
      }
    },
    "load": {
      "paths": [
        "<QuantClaw 目录>/extensions/quantclaw-auth"
      ]
    }
  }
}
```

**注意：** `<QuantClaw 目录>` 替换成你 clone 的实际路径，例如 `/home/ubuntu/QuantClaw`。

### 4. 重启 Clawdbot Gateway

```bash
clawdbot gateway restart
```

验证插件加载：
```bash
clawdbot plugins list
# 应该看到 quantclaw-auth
```

### 5. 启动 Python 服务

```bash
cd server
pip install -r requirements.txt

# 配置环境变量
export GATEWAY_URL=http://127.0.0.1:18789
export GATEWAY_TOKEN=<你的 gateway token>  # 从 ~/.clawdbot/clawdbot.json 的 gateway.auth.token 获取

python app.py
```

服务默认监听 `0.0.0.0:5000`。

### 6. 验证部署

```bash
# 测试 webhook
curl -X POST http://localhost:18789/webhook/quantclaw \
  -H "Content-Type: application/json" \
  -d '{"token":"test123","message":"__auth_check__"}'

# 测试 Python 服务
curl http://localhost:5000/health
```

## 使用 systemd 管理服务（生产环境）

```bash
sudo nano /etc/systemd/system/quantclaw-server.service
```

```ini
[Unit]
Description=QuantClaw Server
After=network.target

[Service]
Type=simple
User=<你的用户名>
WorkingDirectory=<QuantClaw 目录>/server
Environment=GATEWAY_URL=http://127.0.0.1:18789
Environment=GATEWAY_TOKEN=<你的 gateway token>
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable quantclaw-server
sudo systemctl start quantclaw-server
```

## 配置说明

### quantclaw-auth 插件配置

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `dataPath` | `~/.quantclaw/users.json` | 用户数据存储路径 |
| `workspaceBase` | `~/quantclaw-users` | 用户工作区目录 |
| `defaultModel` | `anthropic/claude-sonnet-4-5` | 新用户默认模型 |
| `webhookPath` | `/webhook/quantclaw` | Webhook 路由路径 |
| `webhookSecret` | - | Webhook 签名密钥（可选） |
| `filterMode` | `keywords` | 消息过滤模式：`keywords`/`strict`/`off` |

### Python 服务环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GATEWAY_URL` | `http://127.0.0.1:18789` | Clawdbot Gateway 地址 |
| `GATEWAY_WS` | `ws://127.0.0.1:18789` | WebSocket 地址 |
| `GATEWAY_TOKEN` | - | Gateway 认证 token |

## 开发调试

### 查看日志

```bash
# Clawdbot 日志
journalctl -u clawdbot -f

# Python 服务日志
journalctl -u quantclaw-server -f
```

### 用户管理命令

```bash
clawdbot quantclaw list                    # 列出用户
clawdbot quantclaw info <userId>           # 查看详情
clawdbot quantclaw register <userId>       # 手动注册
clawdbot quantclaw disable <userId>        # 禁用用户
```

---

有问题？提 Issue 或联系 FourierAlpha。
