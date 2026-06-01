# QuantClaw 统一日志模块

**路径**: `scripts/logging/`

## 📝 功能

统一的 API 请求日志和错误日志记录，按 agent_id 和日期自动分类存储。

## 📦 安装/导入

### 方式 1: 直接导入（推荐）

```python
from scripts.logging import log_http_request, log_error, ErrorType

# 记录 API 请求
log_http_request(
    url="https://api.example.com/data",
    data={"param": "value"},
    response={"status": "ok"},
    agent_id="qc-123"
)

# 记录错误
log_error(
    error_msg="连接超时",
    error_type=ErrorType.NETWORK,
    exception=e,
    context={"function": "fetch_data"},
    agent_id="qc-123"
)
```

### 方式 2: sys.path 注入（旧代码兼容）

如果你的脚本在 `skills/` 目录下，可以这样导入：

```python
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.logging import log_http_request, log_error
```

## 🗂️ 日志存储结构

```
~/.quantclaw/logs/
  ├── qc-456d7573709b/
  │   ├── 2026-06-01.log
  │   ├── 2026-06-02.log
  │   └── ...
  ├── qc-abc123/
  │   └── ...
  └── ...
```

**特点**：
- 按 `agent_id` 分目录
- 按日期分文件（`YYYY-MM-DD.log`）
- 自动清理 7 天前的日志
- JSON Lines 格式（每行一个 JSON 对象）

## 📋 API 参考

### log_http_request

记录 HTTP API 请求日志。

**参数**：
- `url` (str): 请求 URL
- `data` (dict): 请求参数
- `response` (dict, 可选): 响应数据
- `error` (str, 可选): 错误信息
- `error_type` (str, 可选): 错误类型
- `agent_id` (str, 可选): Agent ID（未提供时自动获取）

**示例**：
```python
# 成功请求
log_http_request(
    url="https://api.example.com/backtest",
    data={"coin": "BTC", "strategy_type": 1},
    response={"status": 1, "info": [...]},
    agent_id="qc-123"
)

# 失败请求
log_http_request(
    url="https://api.example.com/backtest",
    data={"coin": "BTC"},
    error="Connection timeout",
    error_type=ErrorType.NETWORK,
    agent_id="qc-123"
)
```

### log_error

记录通用错误日志。

**参数**：
- `error_msg` (str): 错误信息
- `error_type` (str, 可选): 错误类型（自动判断）
- `exception` (Exception, 可选): 异常对象（会记录堆栈）
- `context` (dict, 可选): 上下文信息
- `agent_id` (str, 可选): Agent ID（未提供时自动获取）

**示例**：
```python
try:
    result = some_function(param)
except Exception as e:
    log_error(
        error_msg=str(e),
        exception=e,
        context={"function": "some_function", "param": param},
        agent_id="qc-123"
    )
    raise
```

### ErrorType

错误类型常量。

```python
class ErrorType:
    NETWORK = "network_error"       # 网络错误
    API = "api_error"              # API 业务错误
    PARSE = "parse_error"          # 解析错误
    SCRIPT = "script_error"        # 脚本错误
    VALIDATION = "validation_error" # 验证错误
    UNKNOWN = "unknown_error"      # 未知错误
```

### get_agent_id

自动获取当前 agent_id（回退方案）。

**优先级**：
1. 环境变量 `CLAWDBOT_AGENT_ID` 或 `AGENT_ID`
2. 从 PWD 路径提取（优先 `qc-`，然后去掉 `clawd-` 前缀）
3. 返回 `"unknown"`

**注意**：应该优先使用显式传入的 `agent_id` 参数。

### get_recent_logs

读取最近的日志记录。

**参数**：
- `limit` (int): 返回的最大条数（默认 50）
- `agent_id` (str, 可选): Agent ID
- `days` (int): 读取最近几天的日志（默认 1）

**返回**：日志条目列表

### clear_logs

清空所有日志文件。

**参数**：
- `agent_id` (str, 可选): Agent ID

## 🔄 迁移指南

### 从 `skills/backtest-query/api_logger.py` 迁移

**旧代码**：
```python
from api_logger import log_http_request, log_error
```

**新代码**（推荐）：
```python
from scripts.logging import log_http_request, log_error
```

**兼容方案**（保留旧文件作为 wrapper）：

在 `skills/backtest-query/api_logger.py` 中：
```python
# 向后兼容 wrapper
from scripts.logging import *
```

## 📊 日志格式

### HTTP 请求日志
```json
{
  "type": "http_request",
  "timestamp": "2026-06-01T13:45:23.123456",
  "url": "https://api.example.com/endpoint",
  "params": {"usertoken": "abc***def", "coin": "BTC"},
  "response": {"status": 1, "info": [...]},
  "success": true
}
```

### 错误日志
```json
{
  "type": "script_error",
  "timestamp": "2026-06-01T13:45:23.123456",
  "error": "Connection timeout",
  "error_type": "network_error",
  "success": false,
  "exception_type": "TimeoutError",
  "traceback": "...",
  "context": {"function": "fetch_data", "param": "value"}
}
```

## ⚙️ 配置

### 日志目录
修改 `api_logger.py` 中的 `LOG_BASE_DIR`：
```python
LOG_BASE_DIR = os.path.expanduser("~/.quantclaw/logs")
```

### 日志保留天数
修改 `LOG_RETENTION_DAYS`：
```python
LOG_RETENTION_DAYS = 7  # 保留最近 7 天
```

## 🧪 测试

```bash
cd /home/lh/work/QuantClaw/scripts/logging
python3 api_logger.py
```

## 📝 注意事项

1. **agent_id 是必需的**：虽然可以自动获取，但建议显式传递
2. **敏感信息脱敏**：token 字段会自动脱敏
3. **自动清理**：每次写入都会检查并清理过期日志
4. **回测数据精简**：`Backtrack/lists` 接口响应会自动精简，避免日志过大

## 🔗 相关文档

- [QuantClaw 项目结构](../../README.md)
- [技能开发指南](../../skills/README.md)
