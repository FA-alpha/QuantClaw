# QuantClaw Server - Docker 部署指南

## 📁 文件说明

### 核心服务

- `app_docker.py` - 主服务（HTTP API + WebSocket 代理）
- `quantclaw_webhook.py` - 认证服务（Token 验证 + 用户注册）
- `.env` - 环境变量配置（Docker 容器内路径）
- `.env.example` - 配置示例

### 启动脚本

**在容器内使用：**
- `start_docker.sh` - 启动两个服务（在容器内执行）
- `stop_docker.sh` - 停止两个服务（在容器内执行）

**在宿主机使用：**
- `start_in_docker.sh` - 从宿主机启动容器内的服务
- `stop_in_docker.sh` - 从宿主机停止容器内的服务

### 其他文件

- `app.py` - 非 Docker 版本（直接在宿主机运行）
- `requirements.txt` - Python 依赖列表
- `data/` - 聊天记录存储目录
- `static/` - 静态文件目录

---

## 🚀 快速启动

### 前置要求

**首次使用需要安装依赖：**

```bash
# 方法一：使用 apt（推荐）
sudo docker exec -u root openclaw-2026518-openclaw-gateway-1 bash -c \
  "apt-get update && apt-get install -y python3-aiohttp"

# 方法二：使用 pip
sudo docker exec openclaw-2026518-openclaw-gateway-1 bash -c \
  "python3 -m pip install --break-system-packages -r /home/node/quantclaw/server/requirements.txt"

# 方法三：自动安装（start_docker.sh 会尝试自动安装）
```

### 方法一：从宿主机启动（推荐）

```bash
# 确保 Docker 容器已运行
cd /home/ubuntu/work/Docker/openclaw-2026.5.18
sudo docker compose up -d

# 启动服务（会自动检查依赖）
cd /home/ubuntu/work/QuantClaw/server
./start_in_docker.sh

# 查看日志
sudo docker exec openclaw-2026518-openclaw-gateway-1 tail -f /tmp/app_docker.log

# 停止服务
./stop_in_docker.sh
```

### 方法二：进入容器内启动

```bash
# 进入容器
sudo docker exec -it openclaw-2026518-openclaw-gateway-1 bash

# 启动服务
cd /home/node/quantclaw/server
./start_docker.sh

# 停止服务
./stop_docker.sh
```

---

## 🔧 服务架构

```
客户端
  ↓ HTTP/WebSocket
宿主机:8081
  ↓ Docker 端口映射
容器:8080 (app_docker.py 主服务)
  ↓ HTTP 调用
容器:8081 (quantclaw_webhook.py 认证服务)
  ↓ HTTP API
外部 Token 验证服务
```

### 端口配置

| 服务 | 容器端口 | 宿主端口 | 功能 |
|------|---------|---------|------|
| app_docker.py | 8080 | 8080 | HTTP API + WebSocket |
| quantclaw_webhook.py | 8081 | - | 认证服务（内部） |

---

## 📋 环境变量

### app_docker.py

```bash
PORT=8080                                       # 服务端口
AUTH_SERVICE_URL=http://127.0.0.1:8081        # 认证服务地址
GATEWAY_TOKEN=xxx                              # OpenClaw Gateway Token
GATEWAY_URL=http://127.0.0.1:18789           # Gateway HTTP 地址
GATEWAY_WS=ws://127.0.0.1:18789              # Gateway WebSocket 地址
QUANTCLAW_DATA_DIR=/home/node/quantclaw/server/data-docker  # 聊天记录目录（独立）
```

**⚠️ 重要说明：数据目录隔离**

- **宿主机版本** (`app.py`): 使用 `./data/` 目录
- **Docker 版本** (`app_docker.py`): 使用 `./data-docker/` 或容器内独立路径
- **目的**: 避免两个版本的聊天记录混淆，保持数据隔离

### quantclaw_webhook.py

```bash
PORT=8081                                                        # 服务端口
QUANTCLAW_DATA_PATH=/home/node/quantclaw-users/users.json     # 用户数据
QUANTCLAW_WORKSPACE_BASE=/home/node/quantclaw-users            # 工作区根目录
QUANTCLAW_TEMPLATE_PATH=/home/node/quantclaw/templates/...    # 模板路径
QUANTCLAW_SKILLS_PATH=/home/node/quantclaw/skills              # Skills 路径
QUANTCLAW_DEFAULT_MODEL=openrouter/anthropic/claude-sonnet-4.5 # 默认模型
QUANTCLAW_AUTO_REGISTER=true                                    # 自动注册
QUANTCLAW_TOKEN_API=https://...                                 # Token 验证 API
OPENCLAW_CONFIG_PATH=/home/node/.openclaw/openclaw.json        # OpenClaw 配置
```

---

## 🔍 监控与调试

### 查看日志

```bash
# 主服务日志
sudo docker exec openclaw-2026518-openclaw-gateway-1 tail -f /tmp/app_docker.log

# 认证服务日志
sudo docker exec openclaw-2026518-openclaw-gateway-1 tail -f /tmp/quantclaw_webhook.log
```

### 检查服务状态

```bash
# 查看进程
sudo docker exec openclaw-2026518-openclaw-gateway-1 ps aux | grep -E "app_docker|quantclaw_webhook"

# 检查端口
sudo docker exec openclaw-2026518-openclaw-gateway-1 lsof -i:8080
sudo docker exec openclaw-2026518-openclaw-gateway-1 lsof -i:8081

# 健康检查
curl http://localhost:8081/health  # 主服务（从宿主机）
sudo docker exec openclaw-2026518-openclaw-gateway-1 curl -s http://localhost:8080/health  # 主服务（容器内）
sudo docker exec openclaw-2026518-openclaw-gateway-1 curl -s http://localhost:8081/health  # 认证服务（容器内）
```

### 手动重启

```bash
# 停止服务
./stop_in_docker.sh

# 等待 2 秒
sleep 2

# 重新启动
./start_in_docker.sh
```

---

## ⚠️ 常见问题

### 1. 端口冲突

**问题**: `OSError: address already in use`

**解决**:
```bash
# 停止旧进程
sudo docker exec openclaw-2026518-openclaw-gateway-1 pkill -f "quantclaw_webhook|app_docker"

# 或强制杀死
sudo docker exec openclaw-2026518-openclaw-gateway-1 lsof -ti:8080 | xargs kill -9
sudo docker exec openclaw-2026518-openclaw-gateway-1 lsof -ti:8081 | xargs kill -9
```

### 2. aiohttp 未安装

**问题**: `ModuleNotFoundError: No module named 'aiohttp'`

**解决方法一（推荐）- 使用 apt**:
```bash
sudo docker exec -u root openclaw-2026518-openclaw-gateway-1 bash -c \
  "apt-get update && apt-get install -y python3-aiohttp"
```

**解决方法二 - 使用 pip**:
```bash
sudo docker exec openclaw-2026518-openclaw-gateway-1 bash -c \
  "python3 -m pip install --break-system-packages -r /home/node/quantclaw/server/requirements.txt"
```

**解决方法三 - 使用 requirements.txt（宿主机）**:
```bash
# 从宿主机推送文件并安装
cd /home/ubuntu/work/QuantClaw/server
sudo docker exec openclaw-2026518-openclaw-gateway-1 bash -c \
  "pip3 install --break-system-packages -r /home/node/quantclaw/server/requirements.txt"
```

### 3. GATEWAY_TOKEN 未找到

**问题**: `GATEWAY_TOKEN not found`

**解决**:
```bash
# 手动从配置文件提取
sudo docker exec openclaw-2026518-openclaw-gateway-1 python3 -c \
  "import json; print(json.load(open('/home/node/.openclaw/openclaw.json'))['gateway']['auth']['token'])"
```

### 4. 服务启动失败

**检查日志**:
```bash
sudo docker exec openclaw-2026518-openclaw-gateway-1 cat /tmp/app_docker.log
sudo docker exec openclaw-2026518-openclaw-gateway-1 cat /tmp/quantclaw_webhook.log
```

---

## 📝 开发说明

### 修改代码后重启

1. 宿主机编辑文件（会自动同步到容器）:
   ```bash
   vim /home/ubuntu/work/QuantClaw/server/app_docker.py
   ```

2. 重启服务:
   ```bash
   ./stop_in_docker.sh
   ./start_in_docker.sh
   ```

### 添加新的环境变量

1. 编辑 `.env` 文件
2. 重启服务使配置生效

---

## 🔒 安全建议

1. **GATEWAY_TOKEN**: 不要在日志中输出完整 token
2. **用户数据**: 定期备份 `/home/ubuntu/quantclaw-users/`
3. **认证服务**: 8081 端口不对外暴露，仅内部使用
4. **日志轮转**: 定期清理 `/tmp/*.log` 文件

---

## 📞 技术支持

- 项目仓库: `/home/ubuntu/work/QuantClaw`
- Docker Compose: `/home/ubuntu/work/Docker/openclaw-2026.5.18`
- 日志位置: `/tmp/app_docker.log`, `/tmp/quantclaw_webhook.log`
