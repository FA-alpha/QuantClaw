"""
QuantClaw 统一日志模块

提供统一的 API 请求日志、错误日志记录功能。
所有技能和服务都应该使用这个模块记录日志。

使用示例：
    from scripts.logging import log_http_request, log_error, ErrorType
    
    # 记录 API 请求
    log_http_request(url, data, response=result, agent_id=agent_id)
    
    # 记录错误
    log_error(error_msg, exception=e, agent_id=agent_id)
"""

from .api_logger import (
    LOG_ENABLED,
    log_http_request,
    log_error,
    get_agent_id,
    get_log_file_path,
    get_recent_logs,
    clear_logs,
    ErrorType,
)

__all__ = [
    'LOG_ENABLED',
    'log_http_request',
    'log_error',
    'get_agent_id',
    'get_log_file_path',
    'get_recent_logs',
    'clear_logs',
    'ErrorType',
]

__version__ = '1.0.0'
