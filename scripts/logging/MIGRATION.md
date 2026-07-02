# 日志模块迁移指南

## 📍 背景

原本每个 skill 都有自己的 `api_logger.py`，导致：
- ❌ 代码重复
- ❌ 维护困难（需要在多个地方修改）
- ❌ 版本不一致

现在统一到 `scripts/logging/` 目录。

## 🎯 迁移目标

所有技能和服务统一使用 `scripts/logging` 模块。

## 📋 迁移步骤

### 步骤 1: 检查现有代码

查找所有使用 `api_logger` 的地方：

```bash
cd /home/lh/work/QuantClaw
grep -r "from api_logger import" skills/ --include="*.py"
grep -r "import api_logger" skills/ --include="*.py"
```

### 步骤 2: 更新导入语句

#### 选项 A: 最小改动（推荐）

保留现有 `api_logger.py` 作为 wrapper（已完成 ✅）：

```python
# skills/backtest-query/api_logger.py
from scripts.logging import *
```

你的代码**不需要修改**：
```python
from api_logger import log_http_request, log_error  # 仍然有效
```

#### 选项 B: 彻底迁移（未来）

直接使用统一模块：

```python
# 旧代码
from api_logger import log_http_request, log_error

# 新代码
from scripts.logging import log_http_request, log_error
```

### 步骤 3: 删除旧文件（可选）

当所有代码都迁移到新导入方式后，可以删除 wrapper：

```bash
cd /home/lh/work/QuantClaw
rm skills/backtest-query/api_logger.py
rm skills/start-backtest/api_logger.py  # 如果存在
```

## 🗂️ 文件位置对比

### 迁移前
```
skills/backtest-query/api_logger.py   (389 行)
skills/start-backtest/api_logger.py   (可能存在)
... 其他 skill 可能也有 ...
```

### 迁移后
```
scripts/logging/
  ├── __init__.py          # 包入口
  ├── api_logger.py        # 统一实现（389 行）
  ├── README.md            # 使用文档
  └── MIGRATION.md         # 本文件

skills/backtest-query/
  └── api_logger.py        # wrapper（兼容层，30 行）
```

## 🧪 测试迁移结果

### 测试 1: 旧导入方式
```bash
cd /home/lh/work/QuantClaw/skills/backtest-query
python3 -c "from api_logger import log_error, ErrorType; print('✅ 旧方式正常')"
```

### 测试 2: 新导入方式
```bash
cd /home/lh/work/QuantClaw
python3 -c "from scripts.logging import log_error, ErrorType; print('✅ 新方式正常')"
```

### 测试 3: 运行现有脚本
```bash
cd /home/lh/work/QuantClaw/skills/backtest-query
python3 query.py --list-coins --agent-id qc-test
```

检查日志是否正常记录到：
```
~/.quantclaw/logs/qc-test/YYYY-MM-DD.log
```

## 📝 各模块迁移状态

| 模块 | 状态 | 备注 |
|------|------|------|
| `skills/backtest-query` | ✅ 已迁移 | 使用 wrapper 兼容 |
| `skills/start-backtest` | ⏳ 待检查 | 可能有自己的日志系统 |
| 其他 skills | ⏳ 待检查 | 需要逐个排查 |

## 🚀 未来改进

### 阶段 1: 兼容层（当前）
- ✅ 保留 wrapper，现有代码无需修改
- ✅ 新代码推荐使用 `scripts.logging`

### 阶段 2: 逐步迁移
- 🔄 新写的代码直接使用 `scripts.logging`
- 🔄 修改现有代码时顺便更新导入

### 阶段 3: 完全统一
- 📅 所有代码都使用 `scripts.logging`
- 📅 删除所有 wrapper 文件

## ⚠️ 注意事项

1. **不要同时维护两份代码**
   - 只修改 `scripts/logging/api_logger.py`
   - 其他地方的 `api_logger.py` 只作为 wrapper

2. **agent_id 必须传递**
   - 虽然可以自动获取，但强烈建议显式传递
   - 避免日志记录到错误的目录

3. **日志路径不变**
   - 仍然是 `~/.quantclaw/logs/{agent_id}/YYYY-MM-DD.log`
   - 不影响现有日志

## 📞 问题反馈

如果迁移过程中遇到问题，检查：

1. **导入错误**？
   - 确认 `scripts/logging/__init__.py` 存在
   - 检查 Python 路径：`sys.path`

2. **日志未记录**？
   - 确认 `agent_id` 参数传递正确
   - 检查 `~/.quantclaw/logs/` 目录权限

3. **旧代码不工作**？
   - 确认 wrapper 文件存在
   - 检查 wrapper 中的路径设置

---

**迁移完成时间**: 2026-06-01 14:00 GMT+8
