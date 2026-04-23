# Fallback Workspace 方案

## 概述

利用 Clawdbot 的 fallback 机制，预先创建 `clawd-{agentId}` 格式的 workspace，Gateway 会自动发现并使用。

## 原理

### Clawdbot 的 Fallback 行为

当 Gateway 找不到已注册的 agent 时：
1. 尝试查找 `~/clawd-{agentId}` 目录
2. 如果目录存在 → 使用该目录作为 workspace
3. 如果目录不存在 → 创建目录

### 文件不会被覆盖

根据 Clawdbot 文档：
> If any bootstrap file is missing, Clawdbot injects a "missing file" marker into the session and continues.

**意味着**：
- ✅ 已存在的文件 → **保留原样**
- ❌ 缺失的文件 → 注入占位符，但**不会创建新文件**

## 实现方案

### 修改 Plugin

在 `quantclaw-auth` 创建用户时：

```typescript
// 使用 clawd- 前缀（Gateway 会自动发现）
const workspace = this.expandPath(`~/clawd-${agentId}`);

// 从模板复制 MD 文件
await this.createWorkspace(workspace, userId);
```

### 工作流程

```
1. 用户首次访问
   ↓
2. Plugin 创建用户记录
   ↓
3. 创建 /home/ubuntu/clawd-qc-{hash}/
   ├── AGENTS.md    (从模板复制)
   ├── SOUL.md      (从模板复制)
   ├── IDENTITY.md  (从模板复制)
   └── ...
   ↓
4. 返回 agentId: qc-{hash}
   ↓
5. 前端连接 Gateway
   ↓
6. Gateway 查找 agent qc-{hash}
   ↓
7. 未注册 → 使用 fallback
   ↓
8. 发现 ~/clawd-qc-{hash}/ 已存在
   ↓
9. 读取现有文件（不覆盖）
   ↓
10. Agent 正常运行 ✅
```

## 优势

✅ **无需注册** - 不修改 Gateway 配置  
✅ **无需重启** - fallback 机制立即生效  
✅ **文件安全** - Clawdbot 不会覆盖已存在的文件  
✅ **模板生效** - 预先复制的文件会被使用  
✅ **自动清理** - 可以定期清理不活跃的 workspace

## 配置

### Plugin 配置

```json
{
  "plugins": {
    "entries": {
      "quantclaw-auth": {
        "enabled": true,
        "config": {
          "templatePath": "~/work/QuantClaw/templates/agent-workspace",
          "skillsPath": "~/work/QuantClaw/skills"
        }
      }
    }
  }
}
```

### 不需要配置 Gateway

Gateway 保持原样，只有一个 `quantclaw` agent：

```json
{
  "agents": {
    "list": [
      {
        "id": "quantclaw",
        "name": "QuantClaw",
        "workspace": "/home/ubuntu/quantclaw"
      }
    ]
  }
}
```

## 验证

### 测试步骤

```bash
# 1. 清理测试环境
rm -rf ~/clawd-qc-test ~/quantclaw/users.json

# 2. 预先创建 workspace 和模板文件
mkdir -p ~/clawd-qc-test
cp ~/work/QuantClaw/templates/agent-workspace/SOUL.md ~/clawd-qc-test/
echo "# 测试标记" >> ~/clawd-qc-test/SOUL.md

# 3. 模拟用户访问（触发 fallback）
curl -X POST http://localhost:18789/webhook/quantclaw \
  -d '{"token":"test","message":"hello"}'

# 4. 检查文件是否被覆盖
cat ~/clawd-qc-test/SOUL.md
# 应该看到 "# 测试标记" 仍然存在
```

## 限制与权衡

### ✅ 适用场景

- 用户数量可控
- workspace 可以定期清理
- 不需要严格的配置管理

### ❌ 不适合

- 大量用户（数千+）
- 需要严格的 workspace 管理
- 需要动态卸载 agent

### 注意事项

1. **目录命名**：必须使用 `clawd-{agentId}` 格式
2. **文件权限**：确保 Clawdbot 有读写权限
3. **清理策略**：定期清理不活跃的 workspace
4. **监控**：监控 `/home/ubuntu/` 下的 `clawd-*` 目录数量

## 清理脚本

```bash
#!/bin/bash
# 清理超过 30 天未访问的 workspace

find ~/clawd-qc-* -maxdepth 0 -type d -atime +30 | while read dir; do
  echo "清理: $dir"
  rm -rf "$dir"
done
```

## 对比其他方案

| 特性 | Fallback 方案 | 共享 Agent | 动态注册 |
|------|--------------|-----------|---------|
| 注册 agent | ❌ 不需要 | ❌ 不需要 | ✅ 需要 |
| 重启 Gateway | ❌ 不需要 | ❌ 不需要 | ✅ 需要 |
| 独立配置 | ✅ 支持 | ❌ 共享 | ✅ 支持 |
| 独立 workspace | ✅ 支持 | ❌ 共享 | ✅ 支持 |
| 管理复杂度 | 🟡 中等 | 🟢 低 | 🔴 高 |
| 扩展性 | 🟡 中等 | 🟢 好 | 🟡 中等 |

## 结论

**Fallback Workspace 方案** 是当前场景的最佳选择：
- 利用 Clawdbot 原生机制
- 无需修改 Gateway 配置
- 无需重启服务
- 支持用户级配置隔离
- 文件安全有保障

适合 QuantClaw 的多用户场景，在简单性和隔离性之间取得平衡。
