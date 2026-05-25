# QuantClaw + OpenClaw 配置总结

## ✅ 已完成配置

### 1. Docker OpenClaw 容器
- **位置**: `/home/ubuntu/work/Docker/openclaw-2026.5.18`
- **状态**: ✅ 运行正常
- **端口映射**:
  - `19789` → Gateway HTTP
  - `19790` → Gateway Bridge
- **健康检查**: `curl http://127.0.0.1:19789/healthz`

### 2. 目录挂载

| 宿主机目录 | 容器内路径 | 权限 | 用途 |
|-----------|-----------|------|------|
| `/home/ubuntu/quantclaw-users` | `/home/node/quantclaw-users` | `rw` | 用户工作区 |
| `/home/ubuntu/work/QuantClaw/skills` | `/home/node/quantclaw/skills` | `ro` | 技能模块 |
| `/home/ubuntu/work/QuantClaw/templates` | `/home/node/quantclaw/templates` | `ro` | 模板文件 |
| `/home/ubuntu/work/QuantClaw/extensions-dev` | `/home/node/extensions-dev` | `rw` | **插件开发目录** ⭐ |

### 3. QuantClaw Server

#### 原版（Clawdbot 本地）
- **文件**: `app.py`
- **端口**: `18789`
- **启动**: `./start.sh`

#### Docker 版（推荐）✅
- **文件**: `app-docker.py`
- **端口**: `19789`
- **启动**: `./start-docker.sh`
- **健康检查**: `./check-gateway.sh`

---

## 🚀 启动流程

### 完整启动（一键）

```bash
# 1. 启动 Docker 容器
cd /home/ubuntu/work/Docker/openclaw-2026.5.18
sudo docker compose up -d

# 2. 等待容器就绪
sleep 30

# 3. 验证 Gateway
curl http://127.0.0.1:19789/healthz

# 4. 启动 QuantClaw Server
cd /home/ubuntu/work/QuantClaw/server
./start-docker.sh

# 5. （可选）启动 TUI
cd /home/ubuntu/work/Docker/openclaw-2026.5.18
./tui-start.sh
```

---

## 🔧 插件开发流程

### 推荐方式：在 TUI 中让 AI 生成插件

1. **启动 TUI**
   ```bash
   cd /home/ubuntu/work/Docker/openclaw-2026.5.18
   ./tui-start.sh
   ```

2. **请求 AI**
   ```
   请帮我创建一个 OpenClaw 插件：
   
   插件 ID: quantclaw-auth-v2
   目录: /home/node/extensions-dev/quantclaw-auth-v2
   
   功能：
   1. HTTP webhook 端点 /webhook/quantclaw
   2. HMAC 签名验证
   3. 用户自动注册
   4. 消息过滤（关键词 + LLM）
   
   需要的文件：
   - openclaw.plugin.json
   - index.js
   - package.json
   ```

3. **AI 自动生成代码** → 文件出现在 `/home/ubuntu/work/QuantClaw/extensions-dev/quantclaw-auth-v2/`

4. **配置插件**（在 TUI 中或编辑配置文件）
   ```json
   {
     "plugins": {
       "entries": {
         "quantclaw-auth-v2": {
           "enabled": true,
           "config": {
             "webhookPath": "/webhook/quantclaw",
             "webhookSecret": "your-secret"
           }
         }
       }
     }
   }
   ```

5. **重启 Gateway**
   ```bash
   sudo docker compose restart openclaw-gateway
   ```

---

## 📁 目录结构

```
/home/ubuntu/
├── work/
│   ├── Docker/openclaw-2026.5.18/          # Docker 容器配置
│   │   ├── docker-compose.yml              # ✅ 已配置挂载
│   │   └── tui-start.sh                    # TUI 启动脚本
│   └── QuantClaw/
│       ├── server/
│       │   ├── app.py                      # 原版服务端
│       │   ├── app-docker.py               # ✅ Docker 版服务端
│       │   ├── start-docker.sh             # ✅ Docker 启动脚本
│       │   ├── check-gateway.sh            # ✅ Gateway 检查工具
│       │   └── QUICK-START.md              # 快速启动指南
│       ├── extensions-dev/                 # ✅ 插件开发目录 (rw)
│       │   ├── README.md                   # 详细文档
│       │   └── QUICK-GUIDE.md              # 快速指南
│       ├── skills/                         # 技能模块 (ro)
│       └── templates/                      # 模板文件 (ro)
└── quantclaw-users/                        # ✅ 用户工作区 (rw)
```

---

## 🛠️ 常用命令

### Docker 容器管理
```bash
# 启动容器
cd /home/ubuntu/work/Docker/openclaw-2026.5.18
sudo docker compose up -d

# 停止容器
sudo docker compose down

# 重启容器
sudo docker compose restart

# 查看日志
sudo docker logs openclaw-2026518-openclaw-gateway-1 --follow

# 进入容器
sudo docker exec -it openclaw-2026518-openclaw-gateway-1 bash
```

### Gateway 检查
```bash
# 健康检查
curl http://127.0.0.1:19789/healthz

# 检查状态
cd /home/ubuntu/work/QuantClaw/server
./check-gateway.sh
```

### 插件开发
```bash
# 查看插件目录
ls -la /home/ubuntu/work/QuantClaw/extensions-dev

# 在容器内查看
sudo docker exec openclaw-2026518-openclaw-gateway-1 ls -la /home/node/extensions-dev
```

---

## 📚 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 快速启动 | `/home/ubuntu/work/QuantClaw/server/QUICK-START.md` | QuantClaw Server 启动 |
| 版本说明 | `/home/ubuntu/work/QuantClaw/server/README-versions.md` | 原版 vs Docker 版 |
| 插件开发详细 | `/home/ubuntu/work/QuantClaw/extensions-dev/README.md` | 完整开发指南 |
| 插件开发快速 | `/home/ubuntu/work/QuantClaw/extensions-dev/QUICK-GUIDE.md` | 快速上手 |
| 本文件 | `/home/ubuntu/work/QuantClaw/SETUP-SUMMARY.md` | 配置总结 |

---

## 🎯 下一步建议

1. ✅ **Docker 容器正常运行** - 无需操作
2. ✅ **目录挂载配置完成** - 可以开发插件
3. 🚀 **在 TUI 中请求 AI 生成插件** - 最简单的方式
4. 🧪 **测试插件功能** - 在 `extensions-dev` 中迭代
5. 📦 **打包发布** - 稳定后考虑发布

---

**推荐操作：启动 TUI，直接让 AI 帮你生成完整的认证插件代码！** 🚀

```bash
cd /home/ubuntu/work/Docker/openclaw-2026.5.18
./tui-start.sh
```
