#!/usr/bin/env python3
"""
QuantClaw 回测状态监控系统
功能：
1. 多回测并发监控 - 每个回测独立线程
2. 5秒轮询检查状态
3. 完成时通知Agent与用户交互
4. 自动管理监听生命周期

用法:
    # 监控单个回测
    python backtest_monitor.py --token <token> --back-id <回测ID>
    
    # 监控多个回测
    python backtest_monitor.py --token <token> --back-ids <ID1,ID2,ID3>
    
    # 后台守护进程模式
    python backtest_monitor.py --token <token> --back-id <回测ID> --daemon
"""

import argparse
import json
import time
import sys
import os
import requests
import threading
import signal
import logging
from datetime import datetime
from typing import Dict, List, Optional
import subprocess
from dataclasses import dataclass
from enum import Enum

# 配置
API_BASE = "https://www.fourieralpha.com/Mobile"
CHECK_INTERVAL = 5  # 5秒检查一次
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'

# 回测状态枚举
class BacktestStatus(Enum):
    QUEUED = '1'      # 排队
    RUNNING = '2'     # 运行中  
    SUCCESS = '3'     # 成功
    FAILED = '4'      # 失败

@dataclass
class BacktestInfo:
    """回测信息"""
    back_id: str
    status: str
    name: str = ""
    year_rate: str = "N/A"
    sharp_rate: str = "N/A" 
    max_loss: str = "N/A"
    win_rate: str = "N/A"
    trade_num: str = "N/A"
    strategy_num: str = "1"
    bgn_date: str = ""
    end_date: str = ""

class BacktestMonitor:
    """单个回测监控器"""
    
    def __init__(self, token: str, back_id: str, logger: logging.Logger):
        self.token = token
        self.back_id = back_id
        self.logger = logger
        self.stop_flag = threading.Event()
        self.thread = None
        self.start_time = time.time()
        self.check_count = 0
        
    def start(self):
        """启动监控线程"""
        if self.thread and self.thread.is_alive():
            self.logger.warning(f"回测 #{self.back_id} 已在监控中")
            return False
            
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.logger.info(f"🚀 启动回测 #{self.back_id} 监控线程")
        return True
        
    def stop(self):
        """停止监控"""
        self.stop_flag.set()
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info(f"⏹️ 停止回测 #{self.back_id} 监控")
        
    def _get_backtest_info(self) -> Optional[BacktestInfo]:
        """查询回测状态"""
        url = f"{API_BASE}/Backtrack/lists"
        data = {"usertoken": self.token, "back_id": self.back_id}
        
        try:
            resp = requests.post(url, data=data, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            
            # 检查认证状态
            if result.get("status") == 0:
                self.logger.error(f"API错误: {result.get('info', '未知错误')}")
                return None
                
            info_list = result.get("info", [])
            if not info_list:
                self.logger.error(f"回测ID {self.back_id} 不存在")
                return None
                
            raw_info = info_list[0]
            return BacktestInfo(
                back_id=self.back_id,
                status=raw_info.get('status', ''),
                name=raw_info.get('name', ''),
                year_rate=raw_info.get('year_rate', 'N/A'),
                sharp_rate=raw_info.get('sharp_rate', 'N/A'),
                max_loss=raw_info.get('max_loss', 'N/A'), 
                win_rate=raw_info.get('win_rate', 'N/A'),
                trade_num=raw_info.get('trade_num', 'N/A'),
                strategy_num=raw_info.get('strategy_num', '1'),
                bgn_date=raw_info.get('bgn_date', ''),
                end_date=raw_info.get('end_date', '')
            )
            
        except requests.RequestException as e:
            self.logger.error(f"查询回测 #{self.back_id} 失败: {e}")
            return None
            
    def _format_notification_message(self, info: BacktestInfo) -> str:
        """格式化通知消息"""
        status = info.status
        
        if status == BacktestStatus.SUCCESS.value:
            # 成功
            message = f"""🎉 **回测 #{info.back_id} 已完成！**

📊 **回测结果**
• **年化收益率：** {info.year_rate}%
• **夏普比率：** {info.sharp_rate}  
• **最大回撤：** {info.max_loss}%
• **胜率：** {info.win_rate}%
• **交易次数：** {info.trade_num}

📋 **回测信息** 
• **策略数量：** {info.strategy_num}
• **回测时间：** {info.bgn_date} ~ {info.end_date}

🔍 **查看详情：** `python skills/backtest-query/query.py --token <token> --detail {info.back_id}`"""
            
        elif status == BacktestStatus.FAILED.value:
            # 失败
            message = f"""❌ **回测 #{info.back_id} 执行失败**

可能原因：
• 策略配置错误
• 数据不足
• 系统异常

💡 **建议操作：**
• 检查策略参数设置
• 重新提交回测
• 联系技术支持

🔄 **重试回测：** `python skills/start-backtest/start.py --token <token> --apply --strategy-tokens <tokens> --bgn-date <date> --end-date <date>`"""
            
        else:
            # 未知状态
            message = f"⚠️ **回测 #{info.back_id} 状态异常**\n\n当前状态: {status}"
            
        return message
        
    def _notify_agent(self, message: str) -> bool:
        """通知Agent与用户交流"""
        try:
            # 方式1: 使用 clawdbot sessions_send 发送到当前会话
            result = subprocess.run([
                'clawdbot', 'sessions_send',
                '--message', message
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.logger.info(f"✅ 已通知Agent - 回测 #{self.back_id}")
                return True
            else:
                self.logger.error(f"通知Agent失败 (sessions_send): {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.logger.error("通知Agent超时 (sessions_send)")
        except Exception as e:
            self.logger.error(f"通知Agent异常 (sessions_send): {e}")
            
        # 方式2: 备选 - 写入共享文件供Agent读取
        try:
            notification_file = f"/tmp/quantclaw_notification_{self.back_id}.json"
            notification_data = {
                "back_id": self.back_id,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "status": "pending"
            }
            
            with open(notification_file, 'w', encoding='utf-8') as f:
                json.dump(notification_data, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"📝 已写入通知文件: {notification_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"写入通知文件失败: {e}")
            
        return False
        
    def _monitor_loop(self):
        """监控主循环"""
        self.logger.info(f"🔍 开始监控回测 #{self.back_id}")
        
        while not self.stop_flag.is_set():
            self.check_count += 1
            elapsed = int(time.time() - self.start_time)
            
            # 查询状态
            info = self._get_backtest_info()
            if info is None:
                self.logger.warning(f"回测 #{self.back_id} 查询失败，{CHECK_INTERVAL}秒后重试")
                if self.stop_flag.wait(CHECK_INTERVAL):
                    break
                continue
                
            status = info.status
            status_name = {
                '1': '排队中',
                '2': '运行中', 
                '3': '✅成功',
                '4': '❌失败'
            }.get(status, f'未知({status})')
            
            self.logger.info(f"[检查 #{self.check_count}] 回测 #{self.back_id}: {status_name} (已监控{elapsed}秒)")
            
            # 检查是否完成
            if status in [BacktestStatus.SUCCESS.value, BacktestStatus.FAILED.value]:
                self.logger.info(f"🎯 回测 #{self.back_id} 已完成，状态: {status_name}")
                
                # 格式化并发送通知
                notification = self._format_notification_message(info)
                if self._notify_agent(notification):
                    self.logger.info(f"📢 已通知用户 - 回测 #{self.back_id} 结果")
                else:
                    self.logger.error(f"❌ 通知用户失败 - 回测 #{self.back_id}")
                    
                # 监控完成，退出循环
                break
                
            # 等待下次检查
            if self.stop_flag.wait(CHECK_INTERVAL):
                break
                
        self.logger.info(f"🏁 回测 #{self.back_id} 监控结束")

class BacktestMonitorManager:
    """回测监控管理器"""
    
    def __init__(self, token: str):
        self.token = token
        self.monitors: Dict[str, BacktestMonitor] = {}
        self.logger = self._setup_logger()
        self.stop_flag = threading.Event()
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _setup_logger(self) -> logging.Logger:
        """配置日志"""
        logger = logging.getLogger('QuantClawMonitor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(handler)
            
        return logger
        
    def _signal_handler(self, sig, frame):
        """处理退出信号"""
        self.logger.info(f"收到信号 {sig}，正在停止所有监控...")
        self.stop_all()
        sys.exit(0)
        
    def add_monitor(self, back_id: str) -> bool:
        """添加回测监控"""
        if back_id in self.monitors:
            self.logger.warning(f"回测 #{back_id} 已在监控中")
            return False
            
        monitor = BacktestMonitor(self.token, back_id, self.logger)
        if monitor.start():
            self.monitors[back_id] = monitor
            return True
        return False
        
    def remove_monitor(self, back_id: str):
        """移除回测监控"""
        if back_id in self.monitors:
            self.monitors[back_id].stop()
            del self.monitors[back_id]
            self.logger.info(f"已移除回测 #{back_id} 监控")
            
    def stop_all(self):
        """停止所有监控"""
        self.stop_flag.set()
        for back_id in list(self.monitors.keys()):
            self.remove_monitor(back_id)
            
    def list_monitors(self) -> List[str]:
        """列出当前监控的回测"""
        return list(self.monitors.keys())
        
    def wait_for_completion(self):
        """等待所有监控完成"""
        try:
            while self.monitors and not self.stop_flag.is_set():
                # 清理已完成的监控
                completed = []
                for back_id, monitor in self.monitors.items():
                    if not monitor.thread.is_alive():
                        completed.append(back_id)
                        
                for back_id in completed:
                    self.logger.info(f"📋 回测 #{back_id} 监控已自动结束")
                    del self.monitors[back_id]
                    
                if self.monitors:
                    self.logger.info(f"📊 当前监控中: {len(self.monitors)} 个回测 ({', '.join(self.monitors.keys())})")
                    time.sleep(60)  # 每分钟显示一次状态
                else:
                    self.logger.info("✅ 所有回测监控已完成")
                    break
                    
        except KeyboardInterrupt:
            self.logger.info("用户中断，正在停止...")
            self.stop_all()

def main():
    parser = argparse.ArgumentParser(
        description="QuantClaw 回测状态监控系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 监控单个回测
  python backtest_monitor.py --token abc123 --back-id 5745
  
  # 监控多个回测  
  python backtest_monitor.py --token abc123 --back-ids 5745,5746,5747
  
  # 后台守护模式
  python backtest_monitor.py --token abc123 --back-id 5745 --daemon
        """
    )
    
    parser.add_argument("--token", required=True, help="用户认证Token")
    parser.add_argument("--back-id", help="单个回测ID")
    parser.add_argument("--back-ids", help="多个回测ID，逗号分隔")
    parser.add_argument("--daemon", action="store_true", help="后台守护模式")
    parser.add_argument("--list", action="store_true", help="列出当前监控")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")
    
    args = parser.parse_args()
    
    # 配置日志级别
    if args.verbose:
        logging.getLogger('QuantClawMonitor').setLevel(logging.DEBUG)
        
    # 初始化管理器
    manager = BacktestMonitorManager(args.token)
    
    # 列出当前监控（如果有运行中的实例）
    if args.list:
        monitors = manager.list_monitors()
        if monitors:
            print(f"当前监控中的回测: {', '.join(monitors)}")
        else:
            print("当前没有监控中的回测")
        return
        
    # 解析回测ID列表
    back_ids = []
    if args.back_id:
        back_ids.append(args.back_id)
    if args.back_ids:
        back_ids.extend([bid.strip() for bid in args.back_ids.split(',') if bid.strip()])
        
    if not back_ids:
        parser.error("需要指定 --back-id 或 --back-ids")
        
    # 去重
    back_ids = list(set(back_ids))
    
    print(f"🎯 准备监控 {len(back_ids)} 个回测: {', '.join(back_ids)}")
    
    # 添加监控
    success_count = 0
    for back_id in back_ids:
        if manager.add_monitor(back_id):
            success_count += 1
            
    if success_count == 0:
        print("❌ 没有成功启动任何监控")
        sys.exit(1)
        
    print(f"✅ 成功启动 {success_count}/{len(back_ids)} 个监控")
    print(f"🔍 每 {CHECK_INTERVAL} 秒检查一次状态")
    print("按 Ctrl+C 停止监控")
    
    # 等待监控完成
    try:
        manager.wait_for_completion()
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
    finally:
        manager.stop_all()
        print("👋 监控系统已退出")

if __name__ == "__main__":
    main()