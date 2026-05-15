#!/usr/bin/env python3
"""
查看 API 请求日志
"""

import argparse
import json
import os
from datetime import datetime
from api_logger import get_agent_id, get_log_file_path, get_recent_logs, clear_logs, LOG_BASE_DIR


def format_timestamp(ts_str: str) -> str:
    """格式化时间戳"""
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return ts_str


def print_log_entry(entry: dict, verbose: bool = False):
    """打印单条日志"""
    timestamp = format_timestamp(entry.get("timestamp", ""))
    url = entry.get("url", "")
    endpoint = url.split('/')[-1] if url else "未知"
    success = "✅" if entry.get("success") else "❌"
    
    print(f"\n{success} [{timestamp}] {endpoint}")
    
    # 打印参数
    if entry.get("kwargs"):
        print(f"   参数: {json.dumps(entry['kwargs'], ensure_ascii=False)}")
    
    # 打印响应
    if verbose:
        response = entry.get("response")
        if response:
            # 完整显示，不截断
            print(f"   响应: {json.dumps(response, ensure_ascii=False, indent=2)}")
    else:
        # 简要模式
        if entry.get("error"):
            print(f"   错误: {entry['error']}")
        elif "response" in entry:
            resp = entry["response"]
            if isinstance(resp, dict):
                if "info" in resp and isinstance(resp["info"], list):
                    count = len(resp["info"])
                    print(f"   结果: 返回 {count} 条记录")
                elif resp.get("status") == 1:
                    print(f"   结果: 成功")
                else:
                    print(f"   结果: {resp}")
            else:
                print(f"   结果: {resp}")


def main():
    parser = argparse.ArgumentParser(description="查看 API 请求日志")
    parser.add_argument("-n", "--limit", type=int, default=10, help="显示最近 N 条日志")
    parser.add_argument("-d", "--days", type=int, default=1, help="读取最近几天的日志（默认1天）")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")
    parser.add_argument("--clear", action="store_true", help="清空日志文件")
    parser.add_argument("--path", action="store_true", help="显示日志文件路径")
    parser.add_argument("--filter", dest="filter_func", help="过滤特定接口（URL末尾）")
    parser.add_argument("--error-only", action="store_true", help="只显示错误日志")
    parser.add_argument("--agent-id", dest="agent_id", help="指定 Agent ID")
    
    args = parser.parse_args()
    
    agent_id = args.agent_id or get_agent_id()
    
    # 显示路径
    if args.path:
        log_dir = os.path.join(LOG_BASE_DIR, agent_id)
        log_file = get_log_file_path(agent_id)
        print(f"Agent ID: {agent_id}")
        print(f"日志目录: {log_dir}")
        print(f"今日日志: {log_file}")
        return
    
    # 清空日志
    if args.clear:
        clear_logs(agent_id)
        return
    
    # 读取日志
    logs = get_recent_logs(limit=args.limit, agent_id=agent_id, days=args.days)
    
    if not logs:
        print("📭 暂无日志记录")
        return
    
    # 过滤
    if args.filter_func:
        logs = [log for log in logs if args.filter_func in log.get("url", "")]
    
    if args.error_only:
        logs = [log for log in logs if not log.get("success")]
    
    # 显示
    print(f"📊 最近 {len(logs)} 条日志 (Agent: {agent_id}):")
    for log in logs:
        print_log_entry(log, verbose=args.verbose)
    
    log_dir = os.path.join(LOG_BASE_DIR, agent_id)
    print(f"\n💾 日志目录: {log_dir}")


if __name__ == "__main__":
    main()
