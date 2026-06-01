"""
API 日志模块 - 兼容 Wrapper

⚠️ 此文件已迁移到 scripts/logging/api_logger.py
   
为了向后兼容，这里保留一个 wrapper。
新代码应该直接导入：
    from scripts.logging import log_http_request, log_error

旧代码可以继续使用：
    from api_logger import log_http_request, log_error
"""

import sys
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 从统一日志模块导入所有内容
from scripts.logging import *

__all__ = [
    'log_http_request',
    'log_error',
    'get_agent_id',
    'get_log_file_path',
    'get_recent_logs',
    'clear_logs',
    'ErrorType',
]
