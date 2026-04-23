# QuantClaw 管理脚本

## sync-templates.py - 同步模板到现有用户

### 用途

当 `templates/agent-workspace/` 中的模板文件更新后，使用此脚本将更新同步到所有已存在的用户工作区。

### 使用场景

- 修复 SOUL.md 中的能力边界规则
- 更新 AGENTS.md 技能使用指南
- 批量更新所有用户的配置文件
- 选择性更新特定文件（如只更新 SOUL.md）

### 基本用法

```bash
# 1. 预览模式（推荐）- 查看会更新哪些文件
python scripts/sync-templates.py --dry-run

# 2. 更新所有 .md 文件
python scripts/sync-templates.py

# 3. 只更新 SOUL.md
python scripts/sync-templates.py --files SOUL.md

# 4. 更新多个文件
python scripts/sync-templates.py --files SOUL.md AGENTS.md

# 5. 更新除 USER.md 外的所有文件
python scripts/sync-templates.py --exclude USER.md

# 6. 自定义路径
python scripts/sync-templates.py \
  --template-dir ~/work/QuantClaw/templates/agent-workspace \
  --workspace-base ~/quantclaw-users
```

### 安全机制

✅ **自动备份**：更新前自动备份现有文件到 `.backup-YYYYMMDD-HHMMSS/`  
✅ **预览模式**：使用 `--dry-run` 先查看影响范围  
✅ **选择性更新**：可以指定特定文件或排除某些文件  
✅ **版本追踪**：备份目录带时间戳，可回溯历史版本

### 典型工作流

```bash
# 1. 修改模板
vim templates/agent-workspace/SOUL.md

# 2. 预览影响
python scripts/sync-templates.py --files SOUL.md --dry-run

# 3. 确认后执行
python scripts/sync-templates.py --files SOUL.md

# 4. 验证结果
ls ~/quantclaw-users/qc-*/SOUL.md
```

### 输出示例

```
📋 同步模板到现有用户工作区
   模板: /home/ubuntu/work/QuantClaw/templates/agent-workspace
   用户: /home/ubuntu/quantclaw-users
   文件: SOUL.md

🔄 更新: qc-5f041811af40
   ✅ SOUL.md
   💾 备份: /home/ubuntu/quantclaw-users/qc-5f041811af40/.backup-20250519-120000

🔄 更新: qc-e8a8596354e4
   ✅ SOUL.md
   💾 备份: /home/ubuntu/quantclaw-users/qc-e8a8596354e4/.backup-20250519-120001

📊 完成
   更新用户: 2
   更新文件: 2
```

### 注意事项

1. **USER.md 慎重**：此文件包含用户个性化信息，通常应排除
2. **MEMORY.md 慎重**：包含用户历史记忆，不建议覆盖
3. **测试后再批量**：先在测试用户上验证，确认无误后再批量更新
4. **通知用户**：如果更新了关键行为配置（如 SOUL.md），建议通知用户

### Bash 版本

如果不想依赖 Python，也提供了简化的 Bash 版本：

```bash
bash scripts/sync-templates.sh
```

Bash 版本功能较少，只能全量更新所有 .md 文件。

---

## sync-templates.sh - Bash 版本

更简单但功能较少的 Bash 实现。

```bash
# 使用默认路径
bash scripts/sync-templates.sh

# 自定义路径
TEMPLATE_DIR=~/custom/templates \
WORKSPACE_BASE=~/custom/workspaces \
bash scripts/sync-templates.sh
```

---

## 示例：修复 SOUL.md 能力边界

```bash
# 1. 编辑模板
vim templates/agent-workspace/SOUL.md

# 将"执行 shell 命令"从禁止列表移除
# 添加"使用技能查询数据"到允许列表

# 2. 预览影响
python scripts/sync-templates.py --files SOUL.md --dry-run

# 3. 执行同步
python scripts/sync-templates.py --files SOUL.md

# 4. 重启 Gateway 使修改生效
clawdbot gateway restart
```

---

## 恢复备份

如果更新后发现问题，可以从备份恢复：

```bash
# 查看备份
ls ~/quantclaw-users/qc-xxx/.backup-*/

# 恢复单个文件
cp ~/quantclaw-users/qc-xxx/.backup-20250519-120000/SOUL.md \
   ~/quantclaw-users/qc-xxx/SOUL.md

# 恢复所有文件
cp ~/quantclaw-users/qc-xxx/.backup-20250519-120000/* \
   ~/quantclaw-users/qc-xxx/
```
