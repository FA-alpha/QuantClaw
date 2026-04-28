#!/usr/bin/env python3
"""
回测状态监控脚本
用法: python monitor.py --token <token> --back-id <回测ID> [选项]

功能：
- 每5秒查询一次回测状态
- 回测完成后通过聊天通知用户
- 支持多个回测ID同时监控
"""

import argparse
import json
import time
import sys
import os
import requests
from datetime import datetime
import subprocess
import threading
import signal

# API 配置
API_BASE = "https://www.fourieralpha.com/Mobile"

# 监控状态
MONITORING = {}
STOP_FLAG = threading.Event()

def signal_handler(sig, frame):
    """处理Ctrl+C信号"""
    print("\n停止监控...")
    STOP_FLAG.set()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def check_auth(response: dict) -> tuple[bool, str]:
    """检查 API 响应状态"""
    if response.get("status") == 0:
        info = response.get("info", "未知错误")
        return False, str(info)
    return True, ""

def get_backtest_status(token: str, back_id: str) -> dict:
    """
    查询回测状态
    
    Returns:
        dict: 回测信息，包含状态等
    """
    url = f"{API_BASE}/Backtrack/lists"
    data = {
        "usertoken": token,
        "back_id": back_id
    }
    
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        ok, msg = check_auth(result)
        if not ok:
            return {"error": msg}
        
        info = result.get("info", [])
        if info:
            return info[0]  # 返回第一个匹配的回测
        else:
            return {"error": f"回测ID {back_id} 不存在"}
            
    except requests.RequestException as e:
        return {"error": str(e)}

def send_chat_notification(message: str):
    """
    发送聊天通知
    
    通过调用 clawdbot sessions_send 发送消息到当前会话
    """
    try:
        # 获取当前会话信息
        result = subprocess.run([
            'clawdbot', 'sessions_send', 
            '--message', message
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✅ 通知已发送: {message[:50]}...")
        else:
            print(f"❌ 通知发送失败: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("❌ 通知发送超时")
    except Exception as e:
        print(f"❌ 通知发送异常: {e}")

def format_backtest_result(backtest_info: dict) -> str:
    """格式化回测结果"""
    status = backtest_info.get('status', '')
    back_id = backtest_info.get('id', '')
    
    if status == '3':  # 成功
        year_rate = backtest_info.get('year_rate', 'N/A')
        sharp_rate = backtest_info.get('sharp_rate', 'N/A')
        max_loss = backtest_info.get('max_loss', 'N/A')
        win_rate = backtest_info.get('win_rate', 'N/A')
        trade_num = backtest_info.get('trade_num', 'N/A')
        
        message = f"""🎉 回测 #{back_id} 已完成！

📊 **回测结果**
• 年化收益率：{year_rate}%
• 夏普比率：{sharp_rate}
• 最大回撤：{max_loss}%
• 胜率：{win_rate}%
• 交易次数：{trade_num}

查看详情：`python skills/backtest-query/query.py --token <token> --detail {back_id}`"""
        
    elif status == '4':  # 失败
        message = f"""❌ 回测 #{back_id} 执行失败

请检查策略配置或联系技术支持。

重试回测：`python skills/start-backtest/start.py --token <token> --apply --strategy-tokens <tokens> --bgn-date <date> --end-date <date>`"""
    
    else:
        message = f"⚠️ 回测 #{back_id} 状态异常：{status}"
    
    return message

def monitor_backtest(token: str, back_id: str, check_interval: int = 5) -> None:
    """
    监控单个回测
    
    Args:
        token: 用户token
        back_id: 回测ID
        check_interval: 检查间隔（秒）
    """
    print(f"🔍 开始监控回测 #{back_id}，每{check_interval}秒检查一次...")
    
    start_time = time.time()
    check_count = 0
    
    while not STOP_FLAG.is_set():
        check_count += 1
        elapsed = int(time.time() - start_time)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 检查 #{back_id} (第{check_count}次，已监控{elapsed}秒)")
        
        # 查询回测状态
        backtest_info = get_backtest_status(token, back_id)
        
        if "error" in backtest_info:
            print(f"❌ 查询失败: {backtest_info['error']}")
            time.sleep(check_interval)
            continue
        
        status = backtest_info.get('status', '')
        print(f"   状态: {status} ({'成功' if status == '3' else '失败' if status == '4' else '进行中' if status == '2' else '排队' if status == '1' else '未知'})")
        
        # 检查是否完成
        if status in ['3', '4']:  # 成功或失败
            print(f"🎯 回测 #{back_id} 已完成，状态: {status}")
            
            # 发送通知
            notification = format_backtest_result(backtest_info)
            send_chat_notification(notification)
            
            # 从监控列表移除
            if back_id in MONITORING:
                del MONITORING[back_id]
            
            break
        
        # 等待下次检查
        if not STOP_FLAG.wait(check_interval):
            continue
        else:
            break
    
    print(f"✅ 回测 #{back_id} 监控结束")

def start_monitoring_thread(token: str, back_id: str, check_interval: int = 5):
    """在后台线程中启动监控"""
    if back_id in MONITORING:
        print(f"⚠️ 回测 #{back_id} 已在监控中")
        return
    
    # 创建监控线程
    thread = threading.Thread(
        target=monitor_backtest,
        args=(token, back_id, check_interval),
        daemon=True
    )
    
    MONITORING[back_id] = {
        'thread': thread,
        'start_time': time.time()
    }
    
    thread.start()
    print(f"🚀 已启动回测 #{back_id} 的监控线程")

def list_monitoring():
    """列出当前监控的回测"""
    if not MONITORING:
        print("📭 当前没有监控中的回测")
        return
    
    print(f"📋 当前监控中的回测 ({len(MONITORING)} 个):")
    for back_id, info in MONITORING.items():
        elapsed = int(time.time() - info['start_time'])
        print(f"   #{back_id} - 已监控 {elapsed} 秒")

def main():
    parser = argparse.ArgumentParser(description="回测状态监控")
    parser.add_argument("--token", required=True, help="用户token")
    parser.add_argument("--back-id", help="回测ID")
    parser.add_argument("--back-ids", help="多个回测ID（逗号分隔）")
    parser.add_argument("--interval", type=int, default=5, help="检查间隔（秒，默认5）")
    parser.add_argument("--list", action="store_true", help="列出当前监控")
    parser.add_argument("--daemon", action="store_true", help="后台运行模式")
    
    args = parser.parse_args()
    
    # 列出当前监控
    if args.list:
        list_monitoring()
        return
    
    # 验证参数
    if not args.back_id and not args.back_ids:
        print("错误: 需要指定 --back-id 或 --back-ids")
        sys.exit(1)
    
    # 解析回测ID列表
    back_ids = []
    if args.back_id:
        back_ids.append(args.back_id)
    if args.back_ids:
        back_ids.extend([bid.strip() for bid in args.back_ids.split(',')])
    
    # 去重
    back_ids = list(set(back_ids))
    
    print(f"📊 准备监控 {len(back_ids)} 个回测: {', '.join(back_ids)}")
    
    if args.daemon:
        # 后台运行模式
        for back_id in back_ids:
            start_monitoring_thread(args.token, back_id, args.interval)
        
        print(f"🌟 监控已启动，按 Ctrl+C 停止")
        
        try:
            while not STOP_FLAG.is_set():
                # 每60秒显示一次状态
                time.sleep(60)
                if MONITORING:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 监控中: {len(MONITORING)} 个回测")
                else:
                    print("✅ 所有回测监控已完成")
                    break
        except KeyboardInterrupt:
            pass
        
    else:
        # 前台运行模式（单个回测）
        if len(back_ids) > 1:
            print("⚠️ 前台模式只支持单个回测，使用 --daemon 监控多个回测")
            back_ids = back_ids[:1]
        
        monitor_backtest(args.token, back_ids[0], args.interval)

if __name__ == "__main__":
    main()