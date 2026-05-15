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


def simplify_backtest_item(item: dict) -> dict:
    """
    精简单个回测记录，只保留关键字段
    避免 config/metrics 等超大字段导致日志文件过大
    """
    return {
        "id": item.get("id"),
        "back_id": item.get("back_id"),
        "name": item.get("name"),
        "coin": item.get("coin"),
        "strategy_type": item.get("strategy_type"),
        "year_rate": item.get("year_rate"),
        "sharp_rate": item.get("sharp_rate"),
        "max_loss": item.get("max_loss"),
        "win_rate": item.get("win_rate"),
        "strategy_token": item.get("strategy_token"),
        "version": item.get("version"),
        "leverage": item.get("leverage"),
        "direction": item.get("direction"),
        "amt_type": item.get("amt_type"),
        "status": item.get("status"),
    }


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
        # 针对 Backtrack/lists 接口做精简处理
        if "Backtrack/lists" in url and isinstance(response, dict):
            if "info" in response and isinstance(response["info"], list):
                simplified_info = [simplify_backtest_item(item) for item in response["info"]]
                # 移除 None 值
                simplified_info = [
                    {k: v for k, v in item.items() if v is not None}
                    for item in simplified_info
                ]
                log_entry["response"] = {
                    **response,
                    "info": simplified_info
                }
            else:
                log_entry["response"] = response
        else:
            # 其他接口完整记录
            log_entry["response"] = response
    
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
