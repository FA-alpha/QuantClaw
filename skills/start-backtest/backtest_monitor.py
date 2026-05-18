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
class StrategyParam:
    """策略参数解析结果"""
    coin: str           # 币种，如BTC、DOGE、SOL
    direction: str      # 方向，如做多、做空
    ai_time_id: Optional[str] = None      # AI时间ID
    ai_time_name: Optional[str] = None    # AI时间名称，如"2025年震荡"

@dataclass
class AllocationRequirement:
    """保证金分配方案需求"""
    coin_long_pairs: List[str]     # 需要的币种做多组合，如["BTC", "DOGE", "SOL"]
    coin_short_pairs: List[str]    # 需要的币种做空组合
    ai_time_types: List[str]       # 需要的AI时间类型，如["2025年震荡", "2025年牛市"]
    has_ai_time: bool              # 是否包含AI时间参数

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
    
    def __init__(self, token: str, back_id: str, logger: logging.Logger, user_id: str = None):
        self.token = token
        self.back_id = back_id
        self.user_id = user_id  # 添加user_id支持
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
                "user_id": self.user_id,  # 添加user_id
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
        
    def add_monitor(self, back_id: str, user_id: str = None) -> bool:
        """添加回测监控"""
        if back_id in self.monitors:
            self.logger.warning(f"回测 #{back_id} 已在监控中")
            return False
            
        monitor = BacktestMonitor(self.token, back_id, self.logger, user_id)
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
    
    parser.add_argument("--token", help="用户认证Token（可选，未提供时自动获取）")
    parser.add_argument("--back-id", help="单个回测ID")
    parser.add_argument("--back-ids", help="多个回测ID，逗号分隔")
    parser.add_argument("--daemon", action="store_true", help="后台守护模式")
    
    # 新增接口查询选项
    parser.add_argument("--list-groups", action="store_true", help="查询用户策略组列表")
    parser.add_argument("--list-strategies", action="store_true", help="查询用户策略列表")
    parser.add_argument("--page", type=int, default=1, help="页码（默认1）")
    parser.add_argument("--limit", type=int, default=-1, help="每页数量（默认-1，获取全部）")
    
    # 保证金分配方案检查
    parser.add_argument("--check-allocation", action="store_true", help="检查保证金分配方案完整性")
    parser.add_argument("--strategy-ids", help="策略ID列表，逗号分隔")
    parser.add_argument("--coin-long-allocation", help="币种做多分配JSON")
    parser.add_argument("--coin-short-allocation", help="币种做空分配JSON") 
    parser.add_argument("--ai-time-allocation", help="AI时间分配JSON")
    parser.add_argument("--name", help="策略名称搜索")
    parser.add_argument("--coin", help="币种筛选")
    parser.add_argument("--amt-type", help="类型筛选: 1现货 2合约")
    parser.add_argument("--status", help="状态筛选")
    parser.add_argument("--list", action="store_true", help="列出当前监控")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")
    
    args = parser.parse_args()
    
    # 自动获取 token（如果未提供）
    if not args.token:
        args.token = auto_get_token()
        if not args.token:
            print("错误: 无法自动获取 token，请手动提供 --token 参数")
            print("检查路径：")
            print("  1. ~/.quantclaw/users.json")
            print("  2. templates/users.json")
            sys.exit(1)
        print(f"[INFO] 自动获取到token: {args.token[:20]}...")
    
    # 处理新增的接口查询
    if args.list_groups:
        print(f"[INFO] 查询策略组列表（第{args.page}页，每页{args.limit}条）")
        result = get_strategy_groups(args.token, args.page, args.limit)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
        
    if args.list_strategies:
        print(f"[INFO] 查询策略列表（第{args.page}页，每页{args.limit}条）")
        # 只传递用户明确指定的参数，不额外制造参数
        result = get_user_strategies(
            token=args.token,
            page=args.page, 
            limit=args.limit,
            search_val=args.name if args.name else None,
            search_coin=args.coin if args.coin else None,
            amt_type=args.amt_type if args.amt_type else None,
            search_status=args.status if args.status else None
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
        
    # 保证金分配方案完整性检查
    if args.check_allocation:
        if not args.strategy_ids or not args.token:
            print("❌ --check-allocation 需要 --strategy-ids 和 --token 参数")
            return
            
        strategy_ids = [sid.strip() for sid in args.strategy_ids.split(",")]
        
        print(f"🔍 分析策略ID: {strategy_ids}")
        
        # 分析策略需求
        requirement = analyze_strategies_for_allocation(strategy_ids, args.token)
        
        print(f"\n📊 策略分析结果:")
        print(f"  币种做多需求: {requirement.coin_long_pairs}")
        print(f"  币种做空需求: {requirement.coin_short_pairs}")  
        print(f"  AI时间类型需求: {requirement.ai_time_types}")
        print(f"  是否需要AI时间参数: {requirement.has_ai_time}")
        
        # 解析用户提供的分配方案
        user_allocation = {}
        
        if args.coin_long_allocation:
            try:
                user_allocation["coin_long_allocation"] = json.loads(args.coin_long_allocation)
            except json.JSONDecodeError:
                print("❌ coin_long_allocation JSON格式错误")
                return
                
        if args.coin_short_allocation:
            try:
                user_allocation["coin_short_allocation"] = json.loads(args.coin_short_allocation)
            except json.JSONDecodeError:
                print("❌ coin_short_allocation JSON格式错误")
                return
                
        if args.ai_time_allocation:
            try:
                user_allocation["ai_time_allocation"] = json.loads(args.ai_time_allocation)
            except json.JSONDecodeError:
                print("❌ ai_time_allocation JSON格式错误")
                return
        
        # 检查完整性
        missing = check_allocation_completeness(requirement, user_allocation)
        
        # 输出结果
        message = format_missing_params_message(requirement, missing)
        print(f"\n{message}")
        
        # 输出JSON格式供Agent使用
        print(f"\n📄 JSON结果:")
        result = {
            "requirement": {
                "coin_long_pairs": requirement.coin_long_pairs,
                "coin_short_pairs": requirement.coin_short_pairs,
                "ai_time_types": requirement.ai_time_types,
                "has_ai_time": requirement.has_ai_time
            },
            "missing": missing,
            "is_complete": not any(missing.values()),
            "message": message
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    
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

# ========================================
# 新增接口函数：Strategy/group_lists 和 Strategy/lists
# ========================================

def get_strategy_groups(token: str, page: int = 1, limit: int = -1) -> dict:
    """
    查询用户当前策略组列表 - Strategy/group_lists接口
    
    Args:
        token: 用户登录token
        page: 页码（默认1）
        limit: 每页数量（默认10）
    
    Returns:
        dict: API响应数据，包含策略组列表
    """
    url = f"{API_BASE}/Strategy/group_lists"
    data = {
        "usertoken": token,
        "app_v": "2.0.0", 
        "lang": 1,
        "page": page,
        "limit": limit
    }
    
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        # 检查认证状态
        if result.get("status") == 0:
            error_msg = result.get("info", "未知错误")
            print(f"[ERROR] Strategy/group_lists API错误: {error_msg}")
            return {"status": "error", "message": error_msg}
            
        return result
        
    except requests.RequestException as e:
        error_msg = f"查询策略组列表失败: {e}"
        print(f"[ERROR] {error_msg}")
        return {"status": "error", "message": error_msg}


def analyze_strategies_for_allocation(strategy_ids: List[str], token: str) -> AllocationRequirement:
    """
    分析选中的策略，确定保证金分配方案需要的参数
    
    Args:
        strategy_ids: 策略ID列表
        token: 用户token
        
    Returns:
        AllocationRequirement: 保证金分配方案需求
    """
    try:
        # 获取策略详情
        strategies_result = get_user_strategies(token, limit=-1)
        
        if strategies_result.get("status") != 1:
            raise Exception(f"获取策略列表失败: {strategies_result.get('msg', '未知错误')}")
            
        all_strategies = strategies_result.get("info", [])
        
        # 筛选出选中的策略
        selected_strategies = []
        for strategy in all_strategies:
            if str(strategy.get("id")) in strategy_ids:
                selected_strategies.append(strategy)
        
        if not selected_strategies:
            raise Exception("未找到选中的策略")
        
        # 解析策略参数
        coin_long_set = set()
        coin_short_set = set()  
        ai_time_set = set()
        has_ai_time = False
        
        for strategy in selected_strategies:
            coin = strategy.get("coin", "").upper()
            direction = strategy.get("direction", "")
            
            # 收集币种和方向组合（支持中英文）
            if "做多" in direction or "long" in direction.lower():
                coin_long_set.add(coin)
            elif "做空" in direction or "short" in direction.lower():
                coin_short_set.add(coin)
                
            # 检查是否有AI时间参数
            ai_time_id = strategy.get("ai_time_id")
            ai_time_name = strategy.get("ai_time_name") 
            
            if ai_time_id or ai_time_name:
                has_ai_time = True
                if ai_time_name:
                    ai_time_set.add(ai_time_name)
        
        return AllocationRequirement(
            coin_long_pairs=sorted(list(coin_long_set)),
            coin_short_pairs=sorted(list(coin_short_set)),
            ai_time_types=sorted(list(ai_time_set)),
            has_ai_time=has_ai_time
        )
        
    except Exception as e:
        print(f"❌ 策略分析失败: {e}")
        return AllocationRequirement([], [], [], False)


def check_allocation_completeness(requirement: AllocationRequirement, 
                                user_allocation: Dict[str, Dict[str, float]]) -> Dict[str, List[str]]:
    """
    检查用户提供的保证金分配方案是否完整
    
    Args:
        requirement: 策略分析得出的需求
        user_allocation: 用户提供的分配方案，格式如：
            {
                "coin_long_allocation": {"BTC": 40, "DOGE": 60},
                "coin_short_allocation": {"BTC": 50, "DOGE": 50},  
                "ai_time_allocation": {"2025年震荡": 70, "2025年牛市": 30}
            }
            
    Returns:
        Dict[str, List[str]]: 缺失的参数，格式如：
            {
                "missing_coin_long": ["SOL"],
                "missing_coin_short": ["ETH"], 
                "missing_ai_time": ["2025年牛市"],
                "errors": ["需要AI时间参数但未提供"]
            }
    """
    missing = {
        "missing_coin_long": [],
        "missing_coin_short": [],
        "missing_ai_time": [],
        "errors": []
    }
    
    # 检查币种做多分配
    coin_long_provided = set(user_allocation.get("coin_long_allocation", {}).keys())
    coin_long_required = set(requirement.coin_long_pairs)
    missing["missing_coin_long"] = sorted(list(coin_long_required - coin_long_provided))
    
    # 检查币种做空分配  
    coin_short_provided = set(user_allocation.get("coin_short_allocation", {}).keys())
    coin_short_required = set(requirement.coin_short_pairs)
    missing["missing_coin_short"] = sorted(list(coin_short_required - coin_short_provided))
    
    # 检查AI时间类型分配
    if requirement.has_ai_time:
        ai_time_provided = set(user_allocation.get("ai_time_allocation", {}).keys())
        ai_time_required = set(requirement.ai_time_types)
        missing["missing_ai_time"] = sorted(list(ai_time_required - ai_time_provided))
        
        if not user_allocation.get("ai_time_allocation"):
            missing["errors"].append("策略包含AI时间参数，需要提供ai_time_allocation")
    
    return missing


def format_missing_params_message(requirement: AllocationRequirement, 
                                 missing: Dict[str, List[str]]) -> str:
    """
    格式化缺失参数提醒消息
    
    Args:
        requirement: 策略需求
        missing: 缺失的参数
        
    Returns:
        str: 格式化的提醒消息
    """
    if not any(missing.values()):
        return "✅ 所有必要参数已提供，可以进行回测"
    
    message_parts = ["❌ 保证金分配参数不完整，请补充：\n"]
    
    # 币种做多缺失
    if missing["missing_coin_long"]:
        message_parts.append(f"📊 币种做多分配缺失：")
        for coin in missing["missing_coin_long"]:
            message_parts.append(f"  - {coin}做多占比：？%")
        message_parts.append("")
    
    # 币种做空缺失  
    if missing["missing_coin_short"]:
        message_parts.append(f"📊 币种做空分配缺失：")
        for coin in missing["missing_coin_short"]:
            message_parts.append(f"  - {coin}做空占比：？%")
        message_parts.append("")
            
    # AI时间类型缺失
    if missing["missing_ai_time"] or missing["errors"]:
        message_parts.append(f"📊 AI时间类型分配缺失：")
        for ai_time in missing["missing_ai_time"]:
            message_parts.append(f"  - {ai_time}占比：？%")
        for error in missing["errors"]:
            message_parts.append(f"  - {error}")
        message_parts.append("")
    
    # 当前需要的完整参数列表
    message_parts.append("📋 当前策略需要的完整参数：")
    if requirement.coin_long_pairs:
        message_parts.append(f"  币种做多：{', '.join(requirement.coin_long_pairs)}")
    if requirement.coin_short_pairs:
        message_parts.append(f"  币种做空：{', '.join(requirement.coin_short_pairs)}")
    if requirement.has_ai_time and requirement.ai_time_types:
        message_parts.append(f"  AI时间类型：{', '.join(requirement.ai_time_types)}")
    
    return "\n".join(message_parts)


def get_user_strategies(token: str, page: int = 1, limit: int = -1, search_val: str = None, 
                       search_coin: str = None, amt_type: str = None, search_status: str = None) -> dict:
    """
    查询用户当前策略列表 - Strategy/lists接口
    
    Args:
        token: 用户登录token
        page: 页码（默认1）
        limit: 每页数量（默认10）
        search_val: 策略名称搜索（可选）
        search_coin: 币种筛选（可选）
        amt_type: 类型筛选，1=现货 2=合约（可选）
        search_status: 状态筛选（可选）
    
    Returns:
        dict: API响应数据，包含策略列表
    """
    url = f"{API_BASE}/Strategy/lists"
    data = {
        "usertoken": token,
        "app_v": "2.0.0",
        "lang": 1, 
        "page": page,
        "limit": limit
    }
    
    # 只添加用户明确指定的可选参数，Agent不要额外制造参数
    if search_val is not None:
        data["search_val"] = search_val
    if search_coin is not None:
        data["search_coin"] = search_coin
    if amt_type is not None:
        data["amt_type"] = amt_type
    if search_status is not None:
        data["search_status"] = search_status
    
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        # 检查认证状态
        if result.get("status") == 0:
            error_msg = result.get("info", "未知错误")
            print(f"[ERROR] Strategy/lists API错误: {error_msg}")
            return {"status": "error", "message": error_msg}
            
        return result
        
    except requests.RequestException as e:
        error_msg = f"查询策略列表失败: {e}"
        print(f"[ERROR] {error_msg}")
        return {"status": "error", "message": error_msg}


if __name__ == "__main__":
    main()