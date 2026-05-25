# 用户工作空间目录结构

## 📂 目录命名规则

### 修改前（原代码）
```
/home/node/clawd-qc-<hash>/
```

**问题**：硬编码路径，不灵活

---

### 修改后（当前）
```
<workspaceBase>/<userId>/
```

**示例**：
```
/home/node/quantclaw-users/
├── u_abc123def456/
│   ├── AGENTS.md
│   ├── SOUL.md
│   ├── MEMORY.md
│   ├── TOOLS.md
│   ├── USER.md
│   ├── IDENTITY.md
│   ├── HEARTBEAT.md
│   └── memory/
└── u_xyz789uvw012/
    └── ...
```

---

## 🔑 用户 ID 生成规则

### 自动注册（`autoRegister`）

**输入**：客户端提供的 token

**生成**：
```javascript
const hash = crypto.createHash('sha256')
  .update(clientToken)
  .digest('hex')
  .substring(0, 12);
const userId = `u_${hash}`;  // 例: u_abc123def456
```

**特点**：
- 同一个 token 总是生成相同的 userId
- 12 字符 hex 编码（48 bit 熵）
- 前缀 `u_` 便于识别

---

### 手动注册（CLI）

**输入**：用户指定的 userId（如 `jason`, `alice`）

**生成**：
```javascript
const userId = inputUserId;  // 直接使用
```

**特点**：
- 可读性强
- 便于管理

---

## 📁 工作空间内容

每个用户工作空间包含：

### 1. Agent 配置文件（从模板复制）

| 文件 | 说明 |
|------|------|
| `AGENTS.md` | Agent 行为定义 |
| `SOUL.md` | 个性和风格 |
| `MEMORY.md` | 记忆索引 |
| `TOOLS.md` | 工具使用说明 |
| `USER.md` | 用户信息 |
| `IDENTITY.md` | 身份定义 |
| `HEARTBEAT.md` | 定时任务 |

### 2. 记忆目录

```
memory/
├── 2026-05-20-btc-analysis.md
├── 2026-05-21-eth-backtest.md
└── ...
```

---

## ⚙️ 配置说明

**文件**：`/home/ubuntu/.openclaw/openclaw.json`

```json
{
  "plugins": {
    "entries": {
      "quantclaw-auth": {
        "config": {
          "workspaceBase": "/home/node/quantclaw-users",
          "templatePath": "/home/node/quantclaw/templates/agent-workspace"
        }
      }
    }
  }
}
```

**路径映射**（Docker）：

| 配置值 | 容器内路径 | 宿主机路径 |
|--------|-----------|-----------|
| `workspaceBase` | `/home/node/quantclaw-users` | `/home/ubuntu/quantclaw-users` |
| `templatePath` | `/home/node/quantclaw/templates/agent-workspace` | `/home/ubuntu/work/QuantClaw/templates/agent-workspace` |

---

## 🛠️ 工作空间创建流程

```
用户首次请求
    ↓
autoRegister(clientToken)
    ↓
生成 userId (u_<hash>)
    ↓
计算 workspace = path.join(workspaceBase, userId)
    ↓
创建目录: mkdir -p /home/node/quantclaw-users/u_abc123def456
    ↓
从 templatePath 复制 *.md 文件
    ↓
更新 quantclaw-users.json
    ↓
返回 User 对象
```

---

## 📋 目录列表示例

```bash
$ ls -la /home/ubuntu/quantclaw-users/

drwxr-xr-x 3 ubuntu ubuntu 4096 u_abc123def456/
drwxr-xr-x 3 ubuntu ubuntu 4096 u_def456ghi789/
drwxr-xr-x 3 ubuntu ubuntu 4096 u_ghi789jkl012/
```

---

## 🔍 查找用户工作空间

**通过 token 查找**：
```bash
# 1. 从数据库获取 userId
USER_ID=$(jq -r --arg token "$TOKEN" '.users[] | select(.token==$token) | .userId' /home/ubuntu/.openclaw/quantclaw-users.json)

# 2. 访问工作空间
ls -la /home/ubuntu/quantclaw-users/$USER_ID/
```

**通过 userId 直接访问**：
```bash
ls -la /home/ubuntu/quantclaw-users/u_abc123def456/
```

---

## ⚠️ 注意事项

### 1. 权限
确保容器用户（UID 1000）可以写入：
```bash
sudo chown -R 1000:1000 /home/ubuntu/quantclaw-users
```

### 2. 命名冲突
- 自动注册使用 hash，基本不会冲突
- 手动注册需要检查 userId 是否已存在

### 3. 磁盘空间
每个用户工作空间约 100KB（模板文件 + 初始记忆）

---

## 🐛 故障排查

### 问题：工作空间未创建

**症状**：数据库有记录，但目录不存在

**排查**：
```bash
# 检查权限
ls -ld /home/ubuntu/quantclaw-users

# 检查模板是否存在
sudo docker exec openclaw-2026518-openclaw-gateway-1 \
  ls /home/node/quantclaw/templates/agent-workspace/

# 查看插件日志
sudo docker logs openclaw-2026518-openclaw-gateway-1 2>&1 | grep quantclaw-auth
```

### 问题：模板文件未复制

**症状**：工作空间是空目录

**解决**：
1. 检查 `templatePath` 配置
2. 确保模板目录已挂载到容器
3. 重新触发注册

---

**最后更新**: 2026-05-20  
**Git commit**: ee7368c
