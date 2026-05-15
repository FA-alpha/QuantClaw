#!/usr/bin/env python3
"""
API 请求日志模块
记录所有 API 请求参数、响应和错误
"""

import json
import os
from datetime import datetime
from typing import Any

# 日志配置
LOG_DIR = os.path.expanduser("~/.quantclaw/logs")
LOG_FILE = os.path.join(LOG_DIR, "api_requests.log")


def ensure_log_dir():
    """确保日志目录存在"""
    os.makedirs(LOG_DIR, exist_ok=True)


def mask_sensitive_data(data: dict) -> dict:
    """脱敏处理敏感信息"""
    if not isinstance(data, dict):
        return data
    
    result = data.copy()
    
    # 脱敏 token 字段
    for key in ['usertoken', 'token']:
        if key in result and result[key]:
            token = str(result[key])
            if len(token) > 14:
                result[key] = f"{token[:10]}...{token[-4:]}"
            else:
                result[key] = "***"
    
    return result


def log_http_request(url: str, data: dict, response: dict = None, error: str = None):
    """
    记录 HTTP 请求日志
    
    Args:
        url: 请求 URL
        data: 请求参数
        response: 响应数据（可选）
        error: 错误信息（可选）
    """
    ensure_log_dir()
    
    # 构建日志条目
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "url": url,
        "params": mask_sensitive_data(data),
    }
    
    if response is not None:
        # 精简响应数据
        if isinstance(response, dict):
            if response.get("status") == 1 and "info" in response:
                info = response["info"]
                if isinstance(info, list):
                    log_entry["response"] = {
                        "status": 1,
                        "count": len(info),
                        "sample": info[0] if info else None,
                    }
                else:
                    log_entry["response"] = response
            else:
                log_entry["response"] = response
        else:
            log_entry["response"] = str(response)[:200]  # 截断
    
    if error:
        log_entry["error"] = error
        log_entry["success"] = False
    else:
        log_entry["success"] = True
    
    # 写入日志文件
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as log_error:
        print(f"⚠️  日志写入失败: {log_error}")


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
        status = "✅" if entry.get('success') else "❌"
        url = entry.get('url', '').split('/')[-1]
        print(f"  {status} [{entry['timestamp']}] {url}")
