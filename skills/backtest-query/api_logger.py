#!/usr/bin/env python3
"""
API 请求日志模块
记录所有 API 请求参数、响应和错误

日志结构：
~/.quantclaw/logs/
  ├── {agent_id}/
  │   ├── 2026-05-15.log
  │   ├── 2026-05-16.log
  │   └── ...
  └── ...
"""

import json
import os
import glob
from datetime import datetime, timedelta
from typing import Any

# 日志配置
LOG_BASE_DIR = os.path.expanduser("~/.quantclaw/logs")
LOG_RETENTION_DAYS = 7  # 保留最近 7 天的日志


def get_agent_id() -> str:
    """
    获取当前 agent ID
    
    优先级：
    1. 环境变量 CLAWDBOT_AGENT_ID 或 AGENT_ID
    2. 从 PWD 环境变量提取（工作区路径）
    3. 从当前路径提取
    
    工作区通常是：/home/ubuntu/{agent_id}
    """
    # 尝试从环境变量获取
    agent_id = os.environ.get('CLAWDBOT_AGENT_ID') or os.environ.get('AGENT_ID')
    if agent_id:
        return agent_id
    
    # 从 PWD 环境变量提取
    pwd = os.environ.get('PWD', os.getcwd())
    
    # 向上查找，直到找到 /home/ubuntu 的直接子目录
    current = pwd
    while current and current != '/' and current != '/home/ubuntu':
        parent = os.path.dirname(current)
        if parent == '/home/ubuntu':
            return os.path.basename(current)
        current = parent
    
    # 回退：使用当前目录名
    return os.path.basename(pwd) or "default"


def get_log_file_path(agent_id: str = None) -> str:
    """
    获取当前日志文件路径
    格式：~/.quantclaw/logs/{agent_id}/{YYYY-MM-DD}.log
    
    Args:
        agent_id: Agent ID，如果为 None 则自动获取
    
    Returns:
        str: 日志文件路径
    """
    if not agent_id:
        agent_id = get_agent_id()
    
    today = datetime.now().strftime("%Y-%m-%d")
    log_dir = os.path.join(LOG_BASE_DIR, agent_id)
    
    # 确保目录存在
    os.makedirs(log_dir, exist_ok=True)
    
    return os.path.join(log_dir, f"{today}.log")


def cleanup_old_logs(agent_id: str = None, retention_days: int = LOG_RETENTION_DAYS):
    """
    清理过期日志文件
    
    Args:
        agent_id: Agent ID，如果为 None 则自动获取
        retention_days: 保留天数
    """
    if not agent_id:
        agent_id = get_agent_id()
    
    log_dir = os.path.join(LOG_BASE_DIR, agent_id)
    if not os.path.exists(log_dir):
        return
    
    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    # 查找所有日志文件
    log_files = glob.glob(os.path.join(log_dir, "*.log"))
    
    for log_file in log_files:
        try:
            # 从文件名提取日期
            filename = os.path.basename(log_file)
            date_str = filename.replace('.log', '')
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            # 如果过期则删除
            if file_date < cutoff_date:
                os.remove(log_file)
                print(f"🗑️  已删除过期日志: {log_file}")
        except Exception as e:
            # 忽略解析错误的文件
            pass


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


def log_http_request(url: str, data: dict, response: dict = None, error: str = None, agent_id: str = None):
    """
    记录 HTTP 请求日志
    
    Args:
        url: 请求 URL
        data: 请求参数
        response: 响应数据（可选）
        error: 错误信息（可选）
        agent_id: Agent ID（可选，自动获取）
    """
    # 获取日志文件路径（按 agent_id 和日期分文件）
    log_file = get_log_file_path(agent_id)
    
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
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        # 定期清理旧日志（每次写入都检查，但实际删除很快）
        cleanup_old_logs(agent_id)
    except Exception as log_error:
        print(f"⚠️  日志写入失败: {log_error}")


def get_recent_logs(limit: int = 50, agent_id: str = None, days: int = 1) -> list:
    """
    读取最近的日志记录
    
    Args:
        limit: 返回的最大条数
        agent_id: Agent ID（可选，自动获取）
        days: 读取最近几天的日志（默认1天）
    
    Returns:
        list: 日志条目列表
    """
    if not agent_id:
        agent_id = get_agent_id()
    
    log_dir = os.path.join(LOG_BASE_DIR, agent_id)
    if not os.path.exists(log_dir):
        return []
    
    # 收集最近 N 天的日志文件
    log_files = []
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"{date_str}.log")
        if os.path.exists(log_file):
            log_files.append(log_file)
    
    # 按文件名倒序（最新的在前）
    log_files.sort(reverse=True)
    
    # 读取日志
    all_logs = []
    try:
        for log_file in log_files:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines:
                if line.strip():
                    all_logs.append(json.loads(line))
        
        # 按时间戳倒序排序
        all_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # 取最新的 N 条
        return all_logs[:limit]
    except Exception as e:
        print(f"读取日志失败: {e}")
        return []


def clear_logs(agent_id: str = None):
    """
    清空所有日志文件
    
    Args:
        agent_id: Agent ID（可选，自动获取）
    """
    if not agent_id:
        agent_id = get_agent_id()
    
    log_dir = os.path.join(LOG_BASE_DIR, agent_id)
    if os.path.exists(log_dir):
        log_files = glob.glob(os.path.join(log_dir, "*.log"))
        for log_file in log_files:
            os.remove(log_file)
        print(f"✅ 已清空所有日志: {log_dir}")
    else:
        print(f"⚠️  日志目录不存在: {log_dir}")


if __name__ == "__main__":
    # 测试日志功能
    agent_id = get_agent_id()
    log_file = get_log_file_path()
    print(f"Agent ID: {agent_id}")
    print(f"今日日志文件: {log_file}")
    print(f"日志保留天数: {LOG_RETENTION_DAYS}")
    print(f"\n最近 10 条日志:")
    for entry in get_recent_logs(10):
        status = "✅" if entry.get('success') else "❌"
        url = entry.get('url', '').split('/')[-1]
        print(f"  {status} [{entry['timestamp']}] {url}")
