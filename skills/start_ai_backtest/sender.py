#!/usr/bin/env python3
"""
sender.py - 回测调度核心模块

功能:
1. 验证时间段价格是否满足市场规则
2. 调用 OKX 获取 K 线数据
3. 调用 AI 回测接口
4. 支持 CLI 调用
"""

import argparse
import json
import yaml
import requests
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from db_connector import DBConnector

# ============================================================
# 日志配置
# ============================================================
ENABLE_DEBUG_LOG = True  # 开启接口请求日志

def _log_network_request(agent_id: str, api_name: str, request_params: Dict, response_data: Optional[Dict] = None):
    """
    记录网络请求和响应日志
    
    Args:
        agent_id: Agent ID
        api_name: 接口名称
        request_params: 请求参数
        response_data: 接口返回的数据
    """
    if not ENABLE_DEBUG_LOG:
        return
    
    try:
        # 创建日志目录：~/.quantclaw/logs/{agent_id}/
        log_base_dir = Path.home() / '.quantclaw' / 'logs' / agent_id
        log_base_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志文件名：yyyy-mm-dd.log
        log_filename = datetime.now().strftime('%Y-%m-%d') + '.log'
        log_path = log_base_dir / log_filename
        
        log_content = f"调用:backtest-optimizer技能[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n"
        log_content += f"接口: {api_name}\n"
        log_content += f"请求参数: {json.dumps(request_params, ensure_ascii=False)}\n"
        log_content += "---\n"
        if response_data is not None:
            log_content += f"返回参数: {json.dumps(response_data, ensure_ascii=False)}\n"
        log_content += "\n"
        
        # 写入日志文件
        with open(log_path, 'a', encoding='utf-8') as log_file:
            log_file.write(log_content)
    
    except Exception as e:
        print(f"❌ 日志记录失败: {e}")

def get_user_token_by_agent_id(agent_id: str) -> Optional[str]:
    """
    根据传入的AgentID获取对应的UserToken
    
    Args:
        agent_id: 机器人的AgentID
    
    Returns:
        UserToken字符串，如果未找到返回None
    """
    try:
        # 确保使用绝对路径
        users_file_path = os.path.expanduser("~/.quantclaw/users.json")
        
        # 检查文件是否存在
        if not os.path.exists(users_file_path):
            print(f"❌ 用户配置文件不存在: {users_file_path}")
            return None
        
        # 读取并解析JSON文件
        with open(users_file_path, 'r') as f:
            users_data = json.load(f)
        
        # 遍历用户列表查找匹配的AgentID
        for user in users_data.get('users', []):
            if user.get('agentId') == agent_id:
                return user.get('token')
        
        return None
    
    except json.JSONDecodeError:
        print(f"❌ JSON解析错误: {users_file_path}")
        return None
    except Exception as e:
        print(f"❌ 获取UserToken时发生错误: {e}")
        return None


def send_lark_alert(webhook: str, message: str, agent_id: Optional[str] = None) -> bool:
    """
    发送 Lark 告警通知
    
    Args:
        webhook: Lark Webhook 地址
        message: 告警消息
        agent_id: Agent ID（用于日志记录）
    
    Returns:
        True 成功，False 失败
    """
    if not webhook:
        print(f"⚠️ 未配置 Lark Webhook，跳过告警")
        return False
    
    payload = {
        "msg_type": "text",
        "content": {"text": message}
    }
    
    try:
        if agent_id:
            _log_network_request(agent_id, "Lark告警", {"message": message}, None)
        
        response = requests.post(webhook, json=payload, timeout=10)
        response.raise_for_status()
        print(f"✅ Lark 告警发送成功")
        
        if agent_id:
            _log_network_request(agent_id, "Lark告警", {"message": message}, {"status": "success"})
        
        return True
    except Exception as e:
        print(f"❌ Lark 告警发送失败: {e}")
        return False


class BacktestSender:
    """回测调度器"""
    
    def __init__(self, config_path: str = "config.yaml", agent_id: Optional[str] = None):
        """初始化
        
        Args:
            config_path: 配置文件路径
            agent_id: 当前Agent的ID（可选）
        """
        # 加载配置
        config_file = Path(__file__).parent / config_path
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.db = DBConnector(config_path)
        self.predefined_coins = self.config['predefined_coins']
        self.time_ranges = self._load_time_ranges()
        
        # Agent ID 和 User Token
        self.agent_id = agent_id or "unknown"
        self.user_token = get_user_token_by_agent_id(self.agent_id) if agent_id else None
    
    def _load_time_ranges(self) -> Dict:
        """加载预定义时间段映射（从 SKILL.md 逻辑转换为代码）"""
        return {
            "long": {
                "熊市": {
                    "BTC": {"start_date": "2025-10-01", "end_date": "2026-02-08"},
                    "ETH": {"start_date": "2025-10-01", "end_date": "2026-02-08"},
                    "SOL": {"start_date": "2025-10-01", "end_date": "2026-02-08"},
                    "DOGE": {"start_date": "2025-10-01", "end_date": "2026-02-08"},
                    "ZEC": {"start_date": "2026-01-01", "end_date": "2026-03-01"},
                    "NEAR": {"start_date": "2024-12-06", "end_date": "2025-04-09"},
                    "XLM": {"start_date": "2025-07-22", "end_date": "2026-05-22"},
                    "HYPE": {"start_date": "2025-11-01", "end_date": "2025-12-31"},
                },
                "牛市": {
                    "default": {"start_date": "2025-04-10", "end_date": "2025-08-14"},
                },
                "震荡": {
                    "BTC": {"start_date": "2024-12-01", "end_date": "2025-12-31"},
                    "ETH": {"start_date": "2024-12-01", "end_date": "2025-12-31"},
                    "SOL": {"start_date": "2024-12-01", "end_date": "2025-12-31"},
                    "DOGE": {"start_date": "2024-12-01", "end_date": "2025-12-31"},
                    "HYPE": {"start_date": "2024-12-01", "end_date": "2025-12-31"},
                    "ZEC": {"start_date": "2024-11-01", "end_date": "2025-08-01"},
                    "NEAR": {"start_date": "2025-04-10", "end_date": "2026-01-14"},
                    "XLM": {"start_date": "2024-02-07", "end_date": "2024-11-03"},
                },
                "过去一年": {
                    "default": {"start_date": "2025-02-07", "end_date": "2026-02-07"},
                    "HYPE": {"start_date": "2025-02-22", "end_date": "2026-02-22"},
                },
            },
            "short": {
                "熊市": {
                    "default": {"start_date": "2025-10-01", "end_date": "2026-02-08"},
                },
                "牛市": {
                    "default": {"start_date": "2025-04-10", "end_date": "2025-08-14"},
                },
                "震荡": {
                    "default": {"start_date": "2024-12-01", "end_date": "2025-12-31"},
                    "HYPE": {"start_date": "2025-02-22", "end_date": "2026-02-22"},
                },
                "过去一年": {
                    "default": {"start_date": "2025-02-07", "end_date": "2026-02-07"},
                    "HYPE": {"start_date": "2025-02-22", "end_date": "2026-02-22"},
                },
            }
        }
    
    def get_time_period(self, coin: str, direction: str, market_type: str) -> Dict[str, str]:
        """获取预定义币种的时间段
        
        Args:
            coin: 币种
            direction: "long" 或 "short"
            market_type: "熊市"/"牛市"/"震荡"/"过去一年"
        
        Returns:
            {"start_date": "...", "end_date": "...", "name": "..."}
        """
        if coin not in self.predefined_coins:
            return None
        
        ranges = self.time_ranges.get(direction, {}).get(market_type, {})
        
        # 优先查找币种特定的时间段
        if coin in ranges:
            period = ranges[coin]
        elif "default" in ranges:
            period = ranges["default"]
        else:
            return None
        
        return {
            "start_date": period["start_date"],
            "end_date": period["end_date"],
            "name": market_type
        }
    
    def validate_price_range(self, coin: str, start_date: str, end_date: str, 
                            market_type: str, type_: str = "swap") -> bool:
        """验证时间段价格是否满足市场规则
        
        Args:
            coin: 币种名称
            start_date: 开始日期 "YYYY-MM-DD"
            end_date: 结束日期 "YYYY-MM-DD"
            market_type: "熊市"/"牛市"/"震荡"
            type_: "swap"（合约）或 "spot"（现货）
        
        Returns:
            True 满足规则，False 不满足
        """
        # 获取起止价格
        start_price = self.db.get_price_at_date(coin, start_date, type_)
        end_price = self.db.get_price_at_date(coin, end_date, type_)
        
        if not start_price or not end_price:
            print(f"❌ 无法获取价格数据: {coin} {start_date} ~ {end_date}")
            return False
        
        # 计算时长（天数）
        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        dt_end = datetime.strptime(end_date, "%Y-%m-%d")
        days = (dt_end - dt_start).days
        
        # 计算价格变化百分比
        price_change_pct = abs((end_price - start_price) / start_price * 100)
        
        # 获取验证规则
        rules = self.config['validation_rules']
        
        print(f"📊 验证数据:")
        print(f"   币种: {coin}")
        print(f"   时间段: {start_date} ~ {end_date} ({days} 天)")
        print(f"   起始价格: {start_price}")
        print(f"   结束价格: {end_price}")
        print(f"   价格变化: {price_change_pct:.2f}%")
        
        # 根据市场类型验证
        if market_type == "熊市":
            rule = rules['bear_market']
            is_drop = end_price < start_price
            drop_pct = (start_price - end_price) / start_price * 100 if is_drop else 0
            valid = is_drop and drop_pct > rule['price_drop_pct'] and days >= rule['min_days']
            print(f"   规则: 下跌 > {rule['price_drop_pct']}% && 时长 >= {rule['min_days']}天")
            print(f"   结果: {'✅ 满足' if valid else '❌ 不满足'}")
            return valid
        
        elif market_type == "牛市":
            rule = rules['bull_market']
            is_rise = end_price > start_price
            rise_pct = (end_price - start_price) / start_price * 100 if is_rise else 0
            valid = is_rise and rise_pct > rule['price_rise_pct'] and days >= rule['min_days']
            print(f"   规则: 上涨 > {rule['price_rise_pct']}% && 时长 >= {rule['min_days']}天")
            print(f"   结果: {'✅ 满足' if valid else '❌ 不满足'}")
            return valid
        
        elif market_type == "震荡":
            rule = rules['sideways']
            valid = price_change_pct < rule['price_change_pct'] and days >= rule['min_days']
            print(f"   规则: 价差 < {rule['price_change_pct']}% && 时长 >= {rule['min_days']}天")
            print(f"   结果: {'✅ 满足' if valid else '❌ 不满足'}")
            return valid
        
        return False
    
    def trigger_okx_fetch(self, coin: str, start_date: str, end_date: str,
                         market_type: str, direction: str, max_evals: int = None,
                         type_: str = "swap") -> bool:
        """调用 OKX 服务获取K线数据并回测
        
        Args:
            coin: 币种名称
            start_date: 开始日期
            end_date: 结束日期
            market_type: 市场类型
            direction: 方向
            max_evals: 回测数量
            type_: "swap" 或 "spot"
        
        Returns:
            True 成功，False 失败
        """
        if max_evals is None:
            max_evals = self.config['defaults']['max_evals']
        
        # 获取默认参数
        defaults = self.config['defaults']
        max_go_pct = defaults['max_go_pct'][direction]
        min_rate = defaults['min_rate']
        
        # 构建 OKX 服务 URL（从配置读取，目前使用占位符）
        okx_config = self.config['services']['okx_fetch']
        if not okx_config.get('enabled'):
            print(f"⚠️ OKX 服务未启用，请在 config.yaml 中配置")
            url = "http://OKX_SERVER_IP:8001/fetch_and_backtest"  # 占位符
        else:
            url = f"http://{okx_config['host']}:{okx_config['port']}{okx_config['endpoint']}"
        
        # 构建请求参数
        payload = {
            "coin": coin,
            "type": type_,
            "start_date": start_date,
            "end_date": end_date,
            "market_type": market_type,
            "direction": direction,
            "max_evals": max_evals,
            "max_go_pct": max_go_pct,
            "min_rate": min_rate
        }
        
        print(f"\n{'='*60}")
        print(f"📡 调用 OKX 服务")
        print(f"{'='*60}")
        print(f"URL: {url}")
        print(f"参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        # 记录请求日志
        _log_network_request(self.agent_id, "OKX服务(/fetch_and_backtest)", payload)
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            print(f"✅ OKX 服务调用成功")
            print(f"   响应: {result}")
            
            # 记录响应日志
            _log_network_request(self.agent_id, "OKX服务(/fetch_and_backtest)", payload, result)
            
            return True
        
        except requests.exceptions.RequestException as e:
            error_result = {"status": "error", "error": str(e)}
            print(f"❌ OKX 服务调用失败: {e}")
            
            # 记录错误日志
            _log_network_request(self.agent_id, "OKX服务(/fetch_and_backtest)", payload, error_result)
            
            return False
    
    def call_ai_backtest(self, start_back_id: int, max_evals: int, coin: str, 
                        direction: str, time_periods: List[Dict]) -> Dict:
        """调用 AI 回测接口
        
        Args:
            start_back_id: 起始 back_id
            max_evals: 单时间段测试次数
            coin: 币种
            direction: "long" 或 "short"
            time_periods: 时间段列表
        
        Returns:
            API 响应结果
        """
        # 获取默认参数
        defaults = self.config['defaults']
        max_go_pct = defaults['max_go_pct'][direction]
        min_rate = defaults['min_rate']
        
        # 构建接口 URL
        service_config = self.config['services']['ai_backtest']
        url = f"http://{service_config['host']}:{service_config['port']}{service_config['endpoint']}"
        
        # 构建请求参数
        payload = {
            "start_backtest_id": start_back_id,
            "max_evals": max_evals,
            "coin": coin,
            "direction": direction,
            "max_go_pct": max_go_pct,
            "min_rate": min_rate,
            "time_periods": time_periods
        }
        
        print(f"\n{'='*60}")
        print(f"📡 调用 AI 回测接口")
        print(f"{'='*60}")
        print(f"URL: {url}")
        print(f"参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        # 记录请求日志
        _log_network_request(self.agent_id, "AI回测接口(/optimize)", payload)
        
        try:
            timeout = service_config['timeout']
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            
            result = response.json()
            print(f"✅ API 调用成功")
            
            # 记录响应日志
            _log_network_request(self.agent_id, "AI回测接口(/optimize)", payload, result)
            
            return result
        
        except requests.exceptions.RequestException as e:
            error_result = {"status": "error", "error": str(e)}
            print(f"❌ API 调用失败: {e}")
            
            # 记录错误日志
            _log_network_request(self.agent_id, "AI回测接口(/optimize)", payload, error_result)
            
            return error_result
    
    def run_backtest(self, coin: str, direction: str, max_evals: int = None, 
                    market_types: List[str] = None) -> bool:
        """执行完整回测流程（主入口）
        
        Args:
            coin: 币种名称
            direction: "long" 或 "short"
            max_evals: 单时间段测试次数（默认从配置读取）
            market_types: 市场类型列表（默认根据 direction 自动确定）
        
        Returns:
            True 成功，False 失败
        """
        print(f"\n{'='*60}")
        print(f"🚀 开始回测任务")
        print(f"{'='*60}")
        print(f"币种: {coin}")
        print(f"方向: {direction}")
        
        # 设置默认值
        if max_evals is None:
            max_evals = self.config['defaults']['max_evals']
        
        if market_types is None:
            if direction == "long":
                market_types = ["震荡", "熊市", "过去一年"]
            else:  # short
                market_types = ["震荡", "牛市", "过去一年"]
        
        print(f"测试数量: {max_evals} × {len(market_types)} = {max_evals * len(market_types)} 条")
        print(f"市场类型: {', '.join(market_types)}")
        
        # 步骤1: 判断是否为预定义币种
        time_periods = []
        if coin in self.predefined_coins:
            print(f"\n✅ {coin} 是预定义币种，使用映射表")
            for mt in market_types:
                period = self.get_time_period(coin, direction, mt)
                if period:
                    time_periods.append(period)
                    print(f"   {mt}: {period['start_date']} ~ {period['end_date']}")
        else:
            print(f"\n⚠️ {coin} 不是预定义币种，需要 Web Search + 验证")
            print(f"⚠️ 请先通过 Web Search 获取时间段，然后使用 validate 命令验证")
            return False
        
        if not time_periods:
            print(f"❌ 未找到有效的时间段")
            return False
        
        # 步骤2: 获取起始 back_id
        max_back_id = self.db.get_max_back_id()
        start_back_id = max_back_id + 1
        total_records = max_evals * len(time_periods)
        end_back_id = start_back_id + total_records - 1
        
        print(f"\n📊 数据库信息:")
        print(f"   当前最大 back_id: {max_back_id}")
        print(f"   新任务 back_id 范围: {start_back_id} ~ {end_back_id}")
        print(f"   总记录数: {total_records}")
        
        # 步骤3: 插入占位记录
        print(f"\n📝 插入占位记录...")
        for period in time_periods:
            back_ids = list(range(start_back_id, start_back_id + max_evals))
            self.db.insert_backtest_placeholders(
                back_ids, coin, 
                period['start_date'], period['end_date'], period['name']
            )
            print(f"   ✅ {period['name']}: {max_evals} 条")
            start_back_id += max_evals
        
        # 步骤4: 插入回测配置（监听用）
        config_id = self.db.insert_backtest_config(
            back_start_id=start_back_id - total_records,
            back_end_id=end_back_id,
            max_evals=max_evals,
            market_count=len(time_periods)
        )
        print(f"   ✅ 配置记录 ID: {config_id}")
        
        # 步骤5: 调用 AI 回测
        result = self.call_ai_backtest(
            start_back_id=start_back_id - total_records,
            max_evals=max_evals,
            coin=coin,
            direction=direction,
            time_periods=time_periods
        )
        
        if result.get('status') == 'error':
            print(f"\n❌ 回测任务失败")
            return False
        
        print(f"\n✅ 回测任务已提交，请使用 monitor_backtest.py 监听进度")
        print(f"   配置 ID: {config_id}")
        print(f"   back_id 范围: {start_back_id - total_records} ~ {end_back_id}")
        
        return True


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Backtest Sender - 回测调度器")
    parser.add_argument('--agent_id', help='Agent ID（用于获取用户Token和记录日志）')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 子命令: run - 执行回测
    run_parser = subparsers.add_parser('run', help='执行回测任务')
    run_parser.add_argument('--coin', required=True, help='币种名称（如 BTC）')
    run_parser.add_argument('--direction', required=True, choices=['long', 'short'], help='方向')
    run_parser.add_argument('--max_evals', type=int, help='单时间段测试次数（默认200）')
    
    # 子命令: validate - 验证价格
    validate_parser = subparsers.add_parser('validate', help='验证时间段价格是否满足规则')
    validate_parser.add_argument('--coin', required=True, help='币种名称')
    validate_parser.add_argument('--start_date', required=True, help='开始日期 YYYY-MM-DD')
    validate_parser.add_argument('--end_date', required=True, help='结束日期 YYYY-MM-DD')
    validate_parser.add_argument('--market_type', required=True, 
                                choices=['熊市', '牛市', '震荡'], help='市场类型')
    validate_parser.add_argument('--type', default='swap', choices=['swap', 'spot'], 
                                help='币种类型（默认 swap）')
    
    # 子命令: trigger_okx - 触发 OKX 获取K线数据
    trigger_parser = subparsers.add_parser('trigger_okx', help='调用 OKX 服务获取K线数据并回测')
    trigger_parser.add_argument('--coin', required=True, help='币种名称')
    trigger_parser.add_argument('--start_date', required=True, help='开始日期 YYYY-MM-DD')
    trigger_parser.add_argument('--end_date', required=True, help='结束日期 YYYY-MM-DD')
    trigger_parser.add_argument('--market_type', required=True, 
                               choices=['熊市', '牛市', '震荡'], help='市场类型')
    trigger_parser.add_argument('--direction', required=True, choices=['long', 'short'], help='方向')
    trigger_parser.add_argument('--max_evals', type=int, help='回测数量（默认200）')
    trigger_parser.add_argument('--type', default='swap', choices=['swap', 'spot'], 
                               help='币种类型（默认 swap）')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    sender = BacktestSender(agent_id=args.agent_id)
    
    if args.command == 'run':
        success = sender.run_backtest(args.coin, args.direction, args.max_evals)
        exit(0 if success else 1)
    
    elif args.command == 'validate':
        valid = sender.validate_price_range(
            args.coin, args.start_date, args.end_date, args.market_type, args.type
        )
        print(f"\n结果: {'通过' if valid else '未通过'}")
        exit(0 if valid else 1)
    
    elif args.command == 'trigger_okx':
        success = sender.trigger_okx_fetch(
            args.coin, args.start_date, args.end_date, args.market_type,
            args.direction, args.max_evals, args.type
        )
        print(f"\n{'✅ 成功' if success else '❌ 失败'}")
        exit(0 if success else 1)


if __name__ == "__main__":
    main()
