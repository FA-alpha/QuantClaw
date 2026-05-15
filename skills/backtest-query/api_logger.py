#!/usr/bin/env python3
"""
API 请求日志模块
记录所有 API 请求参数、响应和错误
"""

import json
import os
from datetime import datetime
from functools import wraps
from typing import Callable, Any

# 日志配置
LOG_DIR = os.path.expanduser("~/.quantclaw/logs")
LOG_FILE = os.path.join(LOG_DIR, "api_requests.log")


def ensure_log_dir():
    """确保日志目录存在"""
    os.makedirs(LOG_DIR, exist_ok=True)


def mask_token(data: dict) -> dict:
    """脱敏处理 token"""
    if not isinstance(data, dict):
        return data
    
    result = data.copy()
    if 'usertoken' in result:
        token = result['usertoken']
        result['usertoken'] = f"{token[:10]}...{token[-4:]}" if len(token) > 14 else "***"
    return result


def log_api_request(func: Callable) -> Callable:
    """
    API 请求日志装饰器
    
    记录内容：
    - 请求时间
    - 函数名
    - 请求参数（脱敏）
    - 响应数据（可选截断）
    - 错误信息
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        ensure_log_dir()
        
        # 记录开始
        timestamp = datetime.now().isoformat()
        func_name = func.__name__
        
        # 脱敏参数
        safe_kwargs = mask_token(kwargs)
        
        log_entry = {
            "timestamp": timestamp,
            "function": func_name,
            "args": args[1:] if args else [],  # 跳过 token
            "kwargs": safe_kwargs,
        }
        
        try:
            # 执行请求
            result = func(*args, **kwargs)
            
            # 记录响应
            if isinstance(result, dict):
                # 如果是成功响应，截断大字段
                if result.get("status") == 1 and "info" in result:
                    info = result["info"]
                    if isinstance(info, list) and len(info) > 0:
                        log_entry["response"] = {
                            "status": 1,
                            "count": len(info),
                            "sample": info[0] if info else None,
                        }
                    else:
                        log_entry["response"] = result
                elif "error" in result:
                    log_entry["response"] = result
                    log_entry["error"] = result["error"]
                else:
                    log_entry["response"] = result
            else:
                log_entry["response"] = str(result)
            
            log_entry["success"] = "error" not in result
            
        except Exception as e:
            # 记录异常
            log_entry["success"] = False
            log_entry["error"] = str(e)
            log_entry["exception"] = type(e).__name__
            raise
        
        finally:
            # 写入日志文件（追加模式）
            try:
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            except Exception as log_error:
                # 日志写入失败不影响主流程
                print(f"⚠️  日志写入失败: {log_error}")
        
        return result
    
    return wrapper


def get_recent_logs(limit: int = 50) -> list:
    """
    读取最近的日志记录
    
    Args:
        limit: 返回的最大条数
    
    Returns:
        list: 日志条目列表
    """
    if not os.path.exists(LOG_FILE):
        return []
    
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # 取最后 N 行
        recent = lines[-limit:] if len(lines) > limit else lines
        return [json.loads(line) for line in recent if line.strip()]
    except Exception as e:
        print(f"读取日志失败: {e}")
        return []


def clear_logs():
    """清空日志文件"""
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
        print(f"✅ 已清空日志: {LOG_FILE}")


if __name__ == "__main__":
    # 测试日志功能
    print(f"日志文件位置: {LOG_FILE}")
    print(f"最近 10 条日志:")
    for entry in get_recent_logs(10):
        print(f"  [{entry['timestamp']}] {entry['function']} - {'✅' if entry['success'] else '❌'}")
