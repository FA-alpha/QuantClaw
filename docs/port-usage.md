# 端口占用情况总结

## 📊 当前端口使用

| 端口 | 服务 | PID | 说明 | 状态 |
|------|------|-----|------|------|
| **443** | nginx | 3473090 | Nginx 反向代理 | 🟢 运行中 |
| **5000** | lark-webhook | 3444103 | Lark Webhook (systemd) | 🟢 运行中 |
| **8080** | quantclaw (app.py) | 650204 | QuantClaw HTTP + WebSocket | 🟢 运行中 |

---

## 🔍 详细说明

### 1. Nginx (443)
```
服务：nginx
监听：0.0.0.0:443 (HTTPS)
用途：反向代理，可能转发到 lark-webhook (5000)
配置：/etc/nginx/sites-enabled/
```

### 2. Lark Webhook (5000)
```
服务：lark-webhook.service
脚本：/home/ubuntu/clawd/skills/lark/scripts/lark_webhook.py
监听：0.0.0.0:5000
环境变量：LARK_WEBHOOK_PORT=5000
进程：PID 3444103 (systemd 管理)
用途：接收 Lark（飞书）消息
```

**SystemD 配置**：
```ini
Environment=LARK_WEBHOOK_PORT=5000
ExecStart=/home/ubuntu/clawd/venv/bin/python3 lark_webhook.py
```

### 3. QuantClaw Server (8080)
```
服务：quantclaw.service
脚本：/home/ubuntu/work/QuantClaw/server/app.py
监听：0.0.0.0:8080
进程：PID 650204 (systemd 管理)
用途：QuantClaw HTTP API + WebSocket
```

---

## 🆕 新服务端口建议

### quantclaw_webhook.py（新增）

**推荐端口选项**：

| 端口 | 优先级 | 理由 |
|------|--------|------|
| **18862** | ⭐⭐⭐ | 与 18861 相邻，易记 |
| **18863** | ⭐⭐ | 备选 |
| **9000** | ⭐ | 常用端口，但可能冲突 |

**启动命令**：
```bash
# 使用 18862 端口
PORT=18862 python3 quantclaw_webhook.py

# 或修改 SystemD 配置
Environment="PORT=18862"
```

---

## 🔄 端口规划建议

### 方案 A：保持独立（推荐）

```
443   → nginx (HTTPS 入口)
5000  → lark-webhook (Lark 飞书)
8080  → app.py (现有 WebSocket)
18862 → quantclaw_webhook.py (新增认证 Webhook)
```

**优点**：
- ✅ 各服务独立，互不影响
- ✅ 可以同时运行
- ✅ 易于调试

**缺点**：
- ❌ 需要维护多个服务

### 方案 B：合并服务

将 `quantclaw_webhook.py` 功能集成到 `app.py`

**优点**：
- ✅ 只需维护一个服务
- ✅ 共享端口（8080）

**缺点**：
- ❌ 需要重构代码
- ❌ 测试工作量大

---

## 📝 Nginx 反向代理配置示例

如果需要通过 443 端口访问多个服务：

```nginx
# /etc/nginx/sites-available/quantclaw

# Lark Webhook
location /lark/ {
    proxy_pass http://127.0.0.1:5000/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}

# QuantClaw Webhook (新增)
location /api/ {
    proxy_pass http://127.0.0.1:18862/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}

# QuantClaw WebSocket
location /ws/ {
    proxy_pass http://127.0.0.1:8080/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

**访问地址**：
- Lark Webhook: `https://your-domain.com/lark/`
- QuantClaw API: `https://your-domain.com/api/chat`
- WebSocket: `wss://your-domain.com/ws/`

---

## ⚠️ 端口冲突检查

### 检查端口占用
```bash
# 检查特定端口
sudo lsof -i :8080

# 检查所有监听端口
netstat -tuln | grep LISTEN

# 检查服务状态
sudo systemctl status quantclaw
sudo systemctl status lark-webhook
```

### 释放端口
```bash
# 停止服务
sudo systemctl stop quantclaw
sudo systemctl stop lark-webhook

# 或杀掉进程
sudo kill -9 <PID>
```

---

## 🎯 建议操作步骤

### 1. 启动 quantclaw_webhook.py（使用 18862 端口）

```bash
cd /home/ubuntu/work/QuantClaw/server
PORT=18862 python3 quantclaw_webhook.py
```

### 2. 验证端口

```bash
# 应该看到 18862 端口
netstat -tuln | grep 18862
```

### 3. 测试服务

```bash
curl http://localhost:18862/health
```

### 4. 配置 SystemD（可选）

```bash
sudo tee /etc/systemd/system/quantclaw-webhook.service > /dev/null <<EOF
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

Environment="PORT=18862"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable quantclaw-webhook
sudo systemctl start quantclaw-webhook
```

---

## 📊 最终端口分配

| 服务 | 端口 | 协议 | 公开 | 用途 |
|------|------|------|------|------|
| Nginx | 443 | HTTPS | ✅ | 反向代理入口 |
| lark-webhook | 5000 | HTTP | ❌ | Lark 内部 |
| app.py | 8080 | HTTP/WS | ❌ | WebSocket |
| quantclaw-webhook | 18862 | HTTP | ❌ | 认证 API |

**外部访问**：全部通过 Nginx (443) 反向代理

---

*更新时间：2026-05-21*
