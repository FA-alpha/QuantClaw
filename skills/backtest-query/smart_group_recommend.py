#!/usr/bin/env python3
"""
智能分组推荐系统
根据用户需求智能分组，每组筛选优质策略，基于详情数据深度分析后形成最优组合
"""

import sys
import os
import json
import argparse
import itertools
import time
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed
from query import query_backtest, get_backtest_detail, get_version_info
from analysis import recommend_combinations


# ==================== 全局日志控制 ====================

def _should_print_warning() -> bool:
    """判断是否应该输出警告信息（可通过环境变量关闭）"""
    return os.environ.get('SUPPRESS_WARNINGS') != '1'


def _should_print_debug() -> bool:
    """判断是否应该输出 DEBUG 信息"""
    return os.environ.get('DEBUG_BACKTEST') == '1'


# ==================== 错误类 ====================

class QueryError(Exception):
    """查询错误"""
    pass


class ValidationError(Exception):
    """参数验证错误"""
    pass


# ==================== 工具函数 ====================

def parse_csv(value: Optional[str]) -> Optional[List[str]]:
    """解析逗号分隔字符串"""
    if not value:
        return None
    return [v.strip() for v in value.split(',')]


def parse_csv_int(value: Optional[str]) -> Optional[List[int]]:
    """解析逗号分隔整数"""
    if not value:
        return None
    return [int(v.strip()) for v in value.split(',')]


def format_params(params: Dict) -> str:
    """格式化参数显示"""
    parts = []
    for key, value in params.items():
        if value is not None:
            parts.append(f"{key}={value}")
    return ', '.join(parts) if parts else '无筛选'


# ==================== Token 管理 ====================

def get_user_token() -> Optional[str]:
    """
    从当前 workspace 自动获取 token
    
    支持两种情况：
    1. 直接在 workspace 内执行：/home/ubuntu/clawd-qc-xxx/skills/...
    2. 通过软链接执行：workspace/skills -> /home/ubuntu/work/QuantClaw/skills
    
    解决方案：优先使用 PWD 环境变量（保留软链接路径），回退到物理路径
    """
    agent_id = None
    
    def find_agent_id_in_path(start_path: str) -> Optional[str]:
        """向上遍历路径查找 clawd-* 目录"""
        current = start_path
        
        while current != '/':
            basename = os.path.basename(current)
            
            if basename.startswith('clawd-'):
                return basename.replace('clawd-', '')
            
            current = os.path.dirname(current)
        
        return None
    
    # 方法1：从 PWD 环境变量获取（保留软链接路径）
    pwd = os.environ.get('PWD')
    if pwd:
        agent_id = find_agent_id_in_path(pwd)
    
    # 方法2：从物理路径查找（回退方案）
    if not agent_id:
        agent_id = find_agent_id_in_path(os.path.abspath(os.getcwd()))
    
    if not agent_id:
        return None
    
    users_file = os.path.expanduser('~/.quantclaw/users.json')
    if not os.path.exists(users_file):
        return None
    
    try:
        with open(users_file, 'r') as f:
            data = json.load(f)
        users = data.get('users', [])
        for user in users:
            if user.get('agentId') == agent_id:
                return user.get('token')
    except Exception:
        pass
    
    return None


# ==================== 参数处理 ====================

def validate_args(args):
    """统一参数验证"""
    # 映射参数验证在 build_query_combinations 中进行
    return None


def build_query_combinations(args, token: str) -> List[Dict]:
    """
    根据参数生成查询组合（统一返回字典列表）
    
    参数优先级体系：
    1. 映射参数（最高优先级）：strategy-version-map, strategy-direction-map, coin-pct-map
    2. 全局参数（中优先级）：versions, directions, search-pcts
    3. 自动查询（最低优先级）：未传参数时自动获取
    
    智能处理参数依赖关系：
    - versions 依赖 strategy_type（从策略的 versions 字段获取）
    - directions 依赖 strategy_type（仅 1, 7, 11 需要方向）
    - search_pcts 依赖 coin（BTC 特殊比例）
    
    Args:
        args: 命令行参数
        token: 用户 token（用于查询默认值）
    
    Returns:
        [{'coin': 'BTC', 'strategy_type': 1, 'direction': 'long', 'version': '4.3', 'version_extra': {...}, ...}, ...]
    """
    from query import get_coin_list, get_ai_time_list, get_ai_strategy_list
    
    # ==================== 解析映射参数 ====================
    strategy_version_map = {}
    strategy_direction_map = {}
    coin_pct_map = {}
    
    if args.strategy_version_map:
        try:
            strategy_version_map = json.loads(args.strategy_version_map)
        except json.JSONDecodeError as e:
            raise ValidationError(f"--strategy-version-map JSON 解析失败: {e}")
    
    if args.strategy_direction_map:
        try:
            strategy_direction_map = json.loads(args.strategy_direction_map)
        except json.JSONDecodeError as e:
            raise ValidationError(f"--strategy-direction-map JSON 解析失败: {e}")
    
    if args.coin_pct_map:
        try:
            coin_pct_map = json.loads(args.coin_pct_map)
        except json.JSONDecodeError as e:
            raise ValidationError(f"--coin-pct-map JSON 解析失败: {e}")
    
    # ==================== 第1步：获取独立参数 ====================
    
    # 1. 币种列表
    if args.coins:
        coins = parse_csv(args.coins)
    else:
        # 查询所有币种
        result = get_coin_list(token)
        if "error" in result:
            if _should_print_warning():
                print(f"⚠️  获取币种列表失败: {result['error']}，使用默认值")
            coins = ["BTC", "ETH", "SOL"]
        else:
            coins = [c["coin"] for c in result.get("info", [])]
            if not coins:
                coins = ["BTC", "ETH", "SOL"]
    
    # 2. 策略类型列表
    if args.strategy_types:
        strategy_types = parse_csv_int(args.strategy_types)
    else:
        # 查询所有策略类型
        result = get_ai_strategy_list(token)
        if "error" in result:
            if _should_print_warning():
                print(f"⚠️  获取策略列表失败: {result['error']}，使用默认值")
            strategy_types = [11, 7, 1]
        else:
            strategy_types = [s["strategy_type"] for s in result.get("info", [])]
            if not strategy_types:
                strategy_types = [11, 7, 1]
    
    # 3. 时间ID列表
    if args.ai_time_ids:
        ai_time_ids = parse_csv(args.ai_time_ids)
    else:
        # 查询所有时间ID
        result = get_ai_time_list(token)
        if "error" in result:
            if _should_print_warning():
                print(f"⚠️  获取时间列表失败: {result['error']}，使用默认值")
            ai_time_ids = ["5"]
        else:
            ai_time_ids = [str(t["id"]) for t in result.get("info", [])]
            if not ai_time_ids:
                ai_time_ids = ["5"]
    
    # ==================== 第2步：获取策略完整信息（用于提取 versions） ====================
    
    strategy_info_map = {}  # {strategy_type: strategy_info}
    result = get_ai_strategy_list(token)
    if "error" not in result:
        for s in result.get("info", []):
            strategy_info_map[s["strategy_type"]] = s
    
    # ==================== 辅助函数 ====================
    
    def find_version_configs(st: int, version_str: str) -> List[Dict]:
        """
        根据版本号查找该策略的完整版本配置
        
        Args:
            st: 策略类型
            version_str: 版本号字符串
        
        Returns:
            版本配置对象列表（可能有多个，如不同 leverage）
        """
        strategy_info = strategy_info_map.get(st)
        if not strategy_info or "versions" not in strategy_info:
            return [{'version': version_str}]
        
        matched = [
            v for v in strategy_info["versions"]
            if str(v.get("version")) == str(version_str)
        ]
        
        return matched if matched else [{'version': version_str}]
    
    def auto_get_versions(st: int) -> List[Dict]:
        """
        自动获取策略的所有版本配置
        
        Args:
            st: 策略类型
        
        Returns:
            版本配置对象列表
        """
        strategy_info = strategy_info_map.get(st)
        if strategy_info and "versions" in strategy_info:
            return strategy_info["versions"]
        else:
            return [None]  # 没有版本信息
    
    def auto_get_directions(st: int) -> List[Optional[str]]:
        """
        根据策略类型自动判断方向
        
        Args:
            st: 策略类型
        
        Returns:
            方向列表
        """
        DIRECTION_REQUIRED_TYPES = {1, 7, 11}
        if st in DIRECTION_REQUIRED_TYPES:
            return ["long", "short"]
        else:
            return [None]
    
    def auto_get_pcts(coin: str) -> List[str]:
        """
        根据币种自动选择比例
        
        Args:
            coin: 币种
        
        Returns:
            比例列表
        """
        is_btc = coin and 'BTC' in coin.upper()
        if is_btc:
            return ['10', '20', '30', '40', '50', '60', '80', '100', '120']
        else:
            return ['60', '80', '100', '120', '140']
    
    # ==================== 第3步：嵌套生成组合（处理依赖关系） ====================
    
    combinations = []
    
    for st in strategy_types:
        # ==================== 优先级1：strategy-version-map ====================
        if str(st) in strategy_version_map:
            version_spec = strategy_version_map[str(st)]
            
            if version_spec is None:
                # null → 自动查询该策略所有版本
                versions_list = auto_get_versions(st)
            
            elif isinstance(version_spec, list):
                versions_list = []
                for item in version_spec:
                    if isinstance(item, str):
                        # 简化格式："4.3" → 查询该版本的所有配置
                        versions_list.extend(find_version_configs(st, item))
                    elif isinstance(item, dict):
                        # 完整配置：{"version": "4.3", "leverage": 3}
                        versions_list.append(item)
                    else:
                        print(f"⚠️  策略 {st} 版本配置格式错误: {item}，跳过")
                
                if not versions_list:
                    print(f"⚠️  策略 {st} 没有匹配的版本配置，跳过该策略")
                    continue
            else:
                print(f"⚠️  策略 {st} 版本配置格式错误: {version_spec}，跳过该策略")
                continue
        
        # ==================== 优先级2：versions（全局参数） ====================
        elif args.versions:
            user_versions = parse_csv(args.versions)
            versions_list = []
            for v in user_versions:
                versions_list.extend(find_version_configs(st, v))
            
            if not versions_list:
                print(f"⚠️  策略 {st} 没有版本 {user_versions}，跳过该策略")
                continue
        
        # ==================== 优先级3：自动查询 ====================
        else:
            versions_list = auto_get_versions(st)
        
        # ==================== 获取该策略的 directions（优先级同上） ====================
        if str(st) in strategy_direction_map:
            direction_spec = strategy_direction_map[str(st)]
            
            if direction_spec is None:
                directions = auto_get_directions(st)
            elif isinstance(direction_spec, list):
                directions = direction_spec
            else:
                print(f"⚠️  策略 {st} 方向配置格式错误: {direction_spec}")
                directions = auto_get_directions(st)
        
        elif args.directions:
            directions = parse_csv(args.directions)
        
        else:
            directions = auto_get_directions(st)
        
        # === 嵌套循环：version → direction → coin → pct → time_id ===
        for version_item in versions_list:
            for direction in directions:
                for coin in coins:
                    # === 获取该币种的 search_pcts（优先级同上） ===
                    if coin in coin_pct_map:
                        pct_spec = coin_pct_map[coin]
                        
                        if pct_spec is None:
                            search_pcts = auto_get_pcts(coin)
                        elif isinstance(pct_spec, list):
                            search_pcts = pct_spec
                        else:
                            print(f"⚠️  币种 {coin} 比例配置格式错误: {pct_spec}")
                            search_pcts = auto_get_pcts(coin)
                    
                    elif args.search_pcts:
                        search_pcts = parse_csv(args.search_pcts)
                    
                    else:
                        search_pcts = auto_get_pcts(coin)
                    
                    for pct in search_pcts:
                        for time_id in ai_time_ids:
                            # === 构建组合 ===
                            combo = {
                                'coin': coin,
                                'strategy_type': st,
                                'direction': direction,
                                'search_pct': pct,
                                'ai_time_id': time_id,
                            }
                            
                            # 处理版本信息
                            if version_item is None:
                                # 没有版本信息，不添加 version 字段
                                pass
                            elif isinstance(version_item, dict):
                                # 提取版本号
                                combo['version'] = version_item.get('version')
                                # 直接使用完整的版本配置对象
                                combo['version_extra'] = version_item
                            
                            combinations.append(combo)
    
    return combinations


def build_detail_criteria(args) -> Optional[Dict]:
    """构建详情筛选条件"""
    criteria = {}
    
    if args.min_total_win_rate:
        criteria['min_total_win_rate'] = args.min_total_win_rate
    if args.min_recent_profit_rate:
        criteria['min_recent_profit_rate'] = args.min_recent_profit_rate
    if args.max_recent_drawdown:
        criteria['max_recent_drawdown'] = args.max_recent_drawdown
    if args.min_trade_count:
        criteria['min_trade_count'] = args.min_trade_count
    if args.min_stability:
        criteria['min_stability'] = args.min_stability
    
    return criteria if criteria else None


# ==================== 批量查询 ====================

def deduplicate_and_add(strategies: List[Dict], all_strategies: List[Dict], seen_ids: Set[str]) -> int:
    """去重并添加策略"""
    new_count = 0
    for strategy in strategies:
        back_id = strategy.get('back_id')
        if back_id and back_id not in seen_ids:
            seen_ids.add(back_id)
            all_strategies.append(strategy)
            new_count += 1
    return new_count


class ParallelQueryExecutor:
    """并行查询执行器（专为 Agent 优化）"""
    
    def __init__(self, max_workers=10, max_qps=20, retry_times=3, verbose=True, log_level="normal"):
        """
        Args:
            max_workers: 并发线程数
            max_qps: 每秒最大查询数
            retry_times: 失败重试次数
            verbose: 是否输出日志
            log_level: 日志级别
                - "quiet": 只输出关键结果
                - "normal": 输出进度和汇总（默认，适合Agent）
                - "detail": 输出每个失败详情（调试用）
        """
        self.max_workers = max_workers
        self.max_qps = max_qps
        self.retry_times = retry_times
        self.verbose = verbose
        self.log_level = log_level
        self.query_lock = Lock()
        self.last_query_time = 0
    
    def _rate_limited_query(self, query_func, **params):
        """限流查询"""
        with self.query_lock:
            # 计算需要等待的时间
            elapsed = time.time() - self.last_query_time
            min_interval = 1.0 / self.max_qps
            
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            
            self.last_query_time = time.time()
        
        # 执行查询
        return query_func(**params)
    
    def _query_with_retry(self, query_func, params):
        """带重试的查询"""
        last_error = None
        
        for attempt in range(self.retry_times):
            try:
                result = self._rate_limited_query(query_func, **params)
                return result
            except Exception as e:
                last_error = e
                if attempt < self.retry_times - 1:
                    time.sleep(0.5 * (attempt + 1))  # 指数退避
        
        return {"error": f"重试{self.retry_times}次失败: {last_error}"}
    
    def batch_query_parallel(self, token, combinations, base_params):
        """
        并行批量查询
        
        Args:
            token: 用户 token
            combinations: 查询组合列表
            base_params: 基础参数
        
        Returns:
            strategies: 策略列表
        """
        total = len(combinations)
        all_strategies = []
        seen_back_ids = set()
        failed_count = 0
        failed_details = []  # 记录失败详情
        
        if self.verbose and self.log_level != "quiet":
            print(f"\n🚀 开始并行查询 {total} 个组合...")
            print(f"   并发: {self.max_workers} 线程, 限流: {self.max_qps} QPS")
            print(f"   预计耗时: ~{total / self.max_qps:.0f} 秒\n")
        
        # 参数映射
        param_mapping = {
            'coin': 'search_coin',
            'strategy_type': 'strategy_type',
            'direction': 'search_direction',
            'search_pct': 'search_pct',
            'ai_time_id': 'ai_time_id',
            'version': 'version',
            'version_extra': 'version_extra'
        }
        
        # 准备查询参数列表
        query_params_list = []
        for combo in combinations:
            params = base_params.copy()
            for key, value in combo.items():
                if value is not None and key in param_mapping:
                    params[param_mapping[key]] = value
            query_params_list.append(params)
        
        # 并行执行
        completed = 0
        milestone_interval = max(1, total // 10)  # 每10%输出一次
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            futures = {
                executor.submit(self._query_with_retry, query_backtest, params): idx
                for idx, params in enumerate(query_params_list)
            }
            
            # 收集结果
            for future in as_completed(futures):
                idx = futures[future]
                completed += 1
                
                try:
                    result = future.result(timeout=30)
                    
                    if "error" in result:
                        failed_count += 1
                        failed_details.append(f"#{idx+1}: {result['error']}")
                        # 只在 detail 模式输出每个失败
                        if self.verbose and self.log_level == "detail":
                            print(f"⚠️  组合 #{idx+1} 查询失败: {result['error']}")
                    else:
                        strategies = result.get("info", [])
                        new_count = deduplicate_and_add(strategies, all_strategies, seen_back_ids)
                
                except Exception as e:
                    failed_count += 1
                    failed_details.append(f"#{idx+1}: {e}")
                    # 只在 detail 模式输出每个异常
                    if self.verbose and self.log_level == "detail":
                        print(f"❌ 组合 #{idx+1} 异常: {e}")
                
                # 里程碑输出
                if self.verbose and self.log_level == "normal" and completed % milestone_interval == 0:
                    progress = completed / total * 100
                    print(f"   进度: {progress:.0f}% ({completed}/{total})")
        
        if self.verbose and self.log_level != "quiet":
            print(f"\n✅ 查询完成:")
            print(f"   成功: {total - failed_count}/{total}")
            print(f"   失败: {failed_count}")
            print(f"   策略数: {len(all_strategies)} (去重后)")
            
            # 失败率过高时给出提示
            if failed_count > total * 0.3:
                print(f"\n⚠️  失败率过高 ({failed_count}/{total} = {failed_count/total*100:.1f}%)")
                print(f"   建议: 降低 --max-qps 或检查网络连接")
                # detail 模式才显示前几个失败原因
                if self.log_level == "detail" and failed_details:
                    print(f"   前5个失败原因:")
                    for detail in failed_details[:5]:
                        print(f"     - {detail}")
            print()
        
        return all_strategies


# ==================== 推荐器类 ====================

class SmartGroupRecommender:
    """智能分组推荐器"""
    
    def __init__(self, token: str, verbose: bool = True):
        self.token = token
        self.verbose = verbose
    
    def log(self, msg: str):
        if self.verbose:
            print(msg)
    
    # ==================== 智能分组策略 ====================
    
    def infer_grouping_strategy(self, query_text: str) -> List[str]:
        """
        根据用户问题推断分组策略
        
        Args:
            query_text: 用户的查询需求描述
        
        Returns:
            分组维度列表，如 ['coin', 'direction']
        """
        query_lower = query_text.lower()
        dimensions = []
        
        # 币种相关
        if any(kw in query_lower for kw in ['币种', '不同币', '多个币', 'btc', 'eth', 'sol', 'coin']):
            dimensions.append('coin')
        
        # 方向相关
        if any(kw in query_lower for kw in ['多空', '方向', '做多', '做空', 'long', 'short', 'direction']):
            dimensions.append('direction')
        
        # 策略类型相关
        if any(kw in query_lower for kw in ['策略类型', '不同策略', '网格', '趋势', 'strategy', 'type']):
            dimensions.append('strategy_type')
        
        # 时间周期相关
        if any(kw in query_lower for kw in ['周期', '时间', '不同时段', 'time', 'period']):
            dimensions.append('ai_time_id')
        
        # 杠杆相关
        if any(kw in query_lower for kw in ['杠杆', 'leverage']):
            dimensions.append('leverage')
        
        # 默认按币种分组
        if not dimensions:
            dimensions = ['coin']
            self.log("⚠️  未识别到明确分组需求，默认按币种分组")
        
        return dimensions
    
    def classify_strategies(self, strategies: List[Dict], group_by: List[str]) -> Dict[Tuple, List[Dict]]:
        """
        按指定维度分组
        
        Args:
            strategies: 策略列表
            group_by: 分组维度
        
        Returns:
            {(分组键): [策略列表]}
        """
        groups = {}
        
        for strategy in strategies:
            key_parts = []
            for dim in group_by:
                value = strategy.get(dim, 'UNKNOWN')
                key_parts.append(str(value))
            
            key = tuple(key_parts)
            if key not in groups:
                groups[key] = []
            groups[key].append(strategy)
        
        return groups
    
    # ==================== 详情深度分析 ====================
    
    def fetch_detail_data(self, strategies: List[Dict], max_fetch: int = 30) -> List[Dict]:
        """
        批量获取详情数据
        
        Args:
            strategies: 策略列表
            max_fetch: 最多获取数量
        
        Returns:
            包含详情的策略列表
        """
        enriched = []
        failed = 0
        
        self.log(f"\n📊 获取详情数据（最多 {max_fetch} 个）...")
        
        for i, strategy in enumerate(strategies[:max_fetch], 1):
            back_id = strategy.get('back_id')
            if not back_id:
                failed += 1
                continue
            
            try:
                detail = get_backtest_detail(self.token, back_id)
                
                if "error" not in detail:
                    # 提取关键详情指标
                    info = detail.get('info', {})
                    strategy['_detail'] = {
                        'total_stat': info.get('total_stat', {}),
                        'recent_stat': info.get('recent_stat', {}),
                        'coin_fee_list': info.get('coin_fee_list', []),
                        'time_line_list': info.get('time_line_list', [])
                    }
                    enriched.append(strategy)
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                continue
        
        self.log(f"   完成: {len(enriched)}/{min(len(strategies), max_fetch)} 成功, {failed} 失败")
        return enriched
    
    def analyze_detail_metrics(self, strategy: Dict) -> Dict[str, float]:
        """
        分析详情数据中的关键指标
        
        Args:
            strategy: 包含 _detail 的策略
        
        Returns:
            指标字典
        """
        detail = strategy.get('_detail', {})
        total_stat = detail.get('total_stat', {})
        recent_stat = detail.get('recent_stat', {})
        
        metrics = {
            # 基础指标（列表数据）
            'year_rate': strategy.get('year_rate', 0),
            'sharp_rate': strategy.get('sharp_rate', 0),
            'max_loss': strategy.get('max_loss', 100),
            
            # 详情指标（total_stat）
            'total_profit_rate': total_stat.get('profit_rate', 0),
            'total_win_rate': total_stat.get('win_rate', 0),
            'total_trade_count': total_stat.get('trade_count', 0),
            'total_max_drawdown': total_stat.get('max_loss', 100),
            
            # 近期指标（recent_stat）
            'recent_profit_rate': recent_stat.get('profit_rate', 0),
            'recent_win_rate': recent_stat.get('win_rate', 0),
            'recent_trade_count': recent_stat.get('trade_count', 0),
            'recent_max_drawdown': recent_stat.get('max_loss', 100),
        }
        
        # 计算稳定性指标
        if metrics['total_profit_rate'] > 0:
            metrics['recent_stability'] = metrics['recent_profit_rate'] / metrics['total_profit_rate']
        else:
            metrics['recent_stability'] = 0
        
        return metrics
    
    def filter_by_detail_criteria(self, strategies: List[Dict], criteria: Dict) -> List[Dict]:
        """
        基于详情指标筛选策略
        
        Args:
            strategies: 包含详情的策略列表
            criteria: 筛选条件
        
        Returns:
            筛选后的策略列表
        """
        filtered = []
        
        for strategy in strategies:
            metrics = self.analyze_detail_metrics(strategy)
            passed = True
            
            if 'min_total_win_rate' in criteria:
                if metrics['total_win_rate'] < criteria['min_total_win_rate']:
                    passed = False
            
            if 'min_recent_profit_rate' in criteria:
                if metrics['recent_profit_rate'] < criteria['min_recent_profit_rate']:
                    passed = False
            
            if 'max_recent_drawdown' in criteria:
                if metrics['recent_max_drawdown'] > criteria['max_recent_drawdown']:
                    passed = False
            
            if 'min_trade_count' in criteria:
                if metrics['total_trade_count'] < criteria['min_trade_count']:
                    passed = False
            
            if 'min_stability' in criteria:
                if metrics['recent_stability'] < criteria['min_stability']:
                    passed = False
            
            if passed:
                strategy['_metrics'] = metrics
                filtered.append(strategy)
        
        return filtered
    
    # ==================== 智能推荐流程 ====================
    
    def get_top_by_multiple_sorts(
        self,
        strategies: List[Dict],
        top_n: int = 5,
        sort_methods: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        按多种排序方式取 Top-N，去重后返回
        
        Args:
            strategies: 策略列表
            top_n: 每种排序方式取几个
            sort_methods: 排序方式列表
        
        Returns:
            去重后的策略列表
        """
        if not sort_methods:
            sort_methods = ['sharpe', 'return', 'drawdown']
        
        selected = {}  # 用 back_id 去重
        
        # 只在开头输出一次排序方式
        if sort_methods and self.verbose:
            self.log(f"   排序: {', '.join(sort_methods)}, 每种取 Top {top_n}")
        
        for method in sort_methods:
            
            if method == 'sharpe':
                sorted_list = sorted(strategies, key=lambda s: s.get('sharp_rate', 0), reverse=True)
            elif method == 'return':
                sorted_list = sorted(strategies, key=lambda s: s.get('year_rate', 0), reverse=True)
            elif method == 'drawdown':
                sorted_list = sorted(strategies, key=lambda s: s.get('max_loss', 100), reverse=False)
            elif method == 'win_rate':
                sorted_list = sorted(strategies, key=lambda s: s.get('_metrics', {}).get('total_win_rate', 0), reverse=True)
            elif method == 'stability':
                sorted_list = sorted(strategies, key=lambda s: s.get('_metrics', {}).get('recent_stability', 0), reverse=True)
            elif method == 'score':
                sorted_list = sorted(
                    strategies,
                    key=lambda s: (s.get('score', 0) or s.get('total_score', 0) or s.get('recommend_score', 0) or s.get('rating', 0)),
                    reverse=True
                )
            elif method.startswith('custom:'):
                field_name = method.split(':', 1)[1]
                sorted_list = sorted(strategies, key=lambda s: s.get(field_name, 0), reverse=True)
                self.log(f"      📌 自定义字段: {field_name}")
            else:
                self.log(f"      ⚠️  未知排序方式: {method}")
                continue
            
            # 取前 N 个（不再逐个输出）
            for strategy in sorted_list[:top_n]:
                back_id = strategy.get('back_id')
                if back_id and back_id not in selected:
                    selected[back_id] = strategy
        
        return list(selected.values())
    
    def smart_recommend(
        self,
        query_text: str,
        strategies: List[Dict],
        top_per_group: int = 5,
        detail_criteria: Optional[Dict] = None,
        max_combinations: int = 10,
        sort_methods: Optional[List[str]] = None,
        api_sort_type: Optional[int] = None
    ) -> Dict:
        """
        智能推荐主流程
        
        Args:
            query_text: 用户查询需求
            strategies: 预先查询的策略列表
            top_per_group: 每组取几个策略
            detail_criteria: 详情筛选条件
            max_combinations: 最多推荐几个组合
            sort_methods: 排序方式列表
            api_sort_type: API排序类型（仅用于日志）
        
        Returns:
            推荐结果
        """
        self.log("="*70)
        self.log("🧠 智能分组推荐系统")
        self.log("="*70)
        
        # 1. 推断分组策略
        self.log(f"\n📝 用户需求: {query_text}")
        group_by = self.infer_grouping_strategy(query_text)
        self.log(f"🎯 分组策略: {' → '.join(group_by)}")
        
        # 2. 使用预先查询的数据
        self.log(f"\n📊 使用预先查询的 {len(strategies)} 条策略")
        
        if not strategies:
            return {"error": "未找到策略"}
        
        # 3. 分组
        groups = self.classify_strategies(strategies, group_by)
        self.log(f"\n📦 分组结果: {len(groups)} 组")
        
        for key, group_strategies in groups.items():
            label = " / ".join([f"{dim}={val}" for dim, val in zip(group_by, key)])
            self.log(f"   - {label}: {len(group_strategies)} 个策略")
        
        # 4. 每组筛选策略
        all_selected = []
        
        if sort_methods:
            self.log(f"\n🎯 每组按多种排序方式筛选策略...")
            self.log(f"   排序方式: {', '.join(sort_methods)}")
            self.log(f"   每种方式取 Top {top_per_group}")
        else:
            self.log(f"\n🎯 每组按默认方式筛选 Top {top_per_group} 策略...")
        
        for key, group_strategies in groups.items():
            label = " / ".join([f"{val}" for val in key])
            self.log(f"\n--- {label} ({len(group_strategies)} 个策略) ---")
            
            top_strategies = self.get_top_by_multiple_sorts(group_strategies, top_n=top_per_group, sort_methods=sort_methods)
            self.log(f"📊 去重后选择 {len(top_strategies)} 个策略")
            
            # 获取详情
            enriched = self.fetch_detail_data(top_strategies, max_fetch=len(top_strategies))
            
            # 基于详情筛选
            if detail_criteria:
                self.log(f"\n🔬 应用详情筛选条件...")
                before = len(enriched)
                enriched = self.filter_by_detail_criteria(enriched, detail_criteria)
                self.log(f"   筛选后剩余: {len(enriched)}/{before}")
            
            all_selected.extend(enriched)
        
        self.log(f"\n✅ 总计选出 {len(all_selected)} 个优质策略")
        
        # 5. 形成策略组合
        if len(all_selected) < 2:
            self.log("⚠️  策略数量不足，无法形成组合")
            return {
                "query": query_text,
                "group_by": group_by,
                "groups": {str(k): len(v) for k, v in groups.items()},
                "total_fetched": len(strategies),
                "total_selected": len(all_selected),
                "selected_strategies": all_selected,
                "combinations": [],
                "criteria": detail_criteria,
                "sort_methods": sort_methods if sort_methods else ['sharpe', 'return', 'drawdown']
            }
        
        self.log(f"\n🎲 生成策略组合（最多 {max_combinations} 个）...")
        
        # 构建偏好参数
        preferences = {}
        if detail_criteria:
            if 'max_recent_drawdown' in detail_criteria:
                preferences['max_drawdown'] = detail_criteria['max_recent_drawdown']
            # 可以根据其他筛选条件动态调整偏好
        
        # 生成多种大小的组合（避免只有1个组合的情况）
        all_combinations = []
        n_strategies = len(all_selected)
        
        # 根据策略数量决定组合大小
        if n_strategies >= 7:
            # 策略充足：生成3种大小（保守、稳健、激进）
            sizes = [3, 5, 7]
        elif n_strategies >= 5:
            # 策略中等：生成2种大小
            sizes = [3, 5]
        elif n_strategies >= 3:
            # 策略较少：生成1-2种大小
            sizes = [max(3, n_strategies - 1), n_strategies - 2] if n_strategies > 4 else [3]
        else:
            # 策略太少，无法生成多个组合
            sizes = [n_strategies]
        
        # 每种大小生成部分组合
        per_size = max(2, max_combinations // len(sizes))
        
        for size in sizes:
            if size <= n_strategies:
                combos = recommend_combinations(
                    strategies=all_selected,
                    group_size=size,
                    top_n=per_size,
                    preferences=preferences if preferences else None
                )
                # 添加组合大小标签
                for combo in combos:
                    if size == 3:
                        combo['style'] = '保守型'
                    elif size == 5:
                        combo['style'] = '稳健型'
                    elif size >= 7:
                        combo['style'] = '激进型'
                    else:
                        combo['style'] = f'{size}策略组合'
                all_combinations.extend(combos)
        
        # 按评分排序，取前 N 个
        all_combinations.sort(key=lambda x: x.get('score', 0), reverse=True)
        combinations = all_combinations[:max_combinations]
        
        # 6. 返回结果
        return {
            "query": query_text,
            "group_by": group_by,
            "groups": {str(k): len(v) for k, v in groups.items()},
            "total_fetched": len(strategies),
            "total_selected": len(all_selected),
            "selected_strategies": all_selected,
            "combinations": combinations,
            "criteria": detail_criteria,
            "sort_methods": sort_methods if sort_methods else ['sharpe', 'return', 'drawdown']
        }
    
    def print_result(self, result: Dict):
        """打印推荐结果"""
        if "error" in result:
            print(f"\n❌ 错误: {result['error']}")
            return
        
        print("\n" + "="*70)
        print("📊 推荐结果摘要")
        print("="*70)
        
        print(f"\n🎯 分组维度: {' → '.join(result.get('group_by', []))}")
        print(f"📦 分组数量: {len(result.get('groups', {}))} 组")
        print(f"🔄 排序方式: {', '.join(result.get('sort_methods', ['sharpe']))}")
        print(f"📊 总共获取: {result.get('total_fetched', 0)} 条策略")
        print(f"✅ 筛选出: {result.get('total_selected', 0)} 条优质策略")
        
        combinations = result.get('combinations', [])
        print(f"\n🌟 推荐组合: {len(combinations)} 个")
        
        if not combinations:
            print("   （无推荐组合）")
            return
        
        for i, combo in enumerate(combinations[:5], 1):
            print(f"\n--- 组合 #{i} ---")
            print(f"评分: {combo['score']:.2f}")
            print(f"预期收益: {combo['expected_return']:.2f}%")
            print(f"组合回撤: {combo['portfolio_risk']['max_drawdown']:.2f}%")
            print(f"策略数量: {len(combo['strategies'])}")
            
            print("策略列表:")
            for j, s in enumerate(combo['strategies'], 1):
                metrics = s.get('_metrics', {})
                print(
                    f"  {j}. {s.get('coin')} / {s.get('name')} "
                    f"(年化{s.get('year_rate')}%, 夏普{s.get('sharp_rate'):.2f}, "
                    f"总胜率{metrics.get('total_win_rate', 0):.1f}%, "
                    f"近期收益{metrics.get('recent_profit_rate', 0):.1f}%)"
                )
            
            # 生成创建命令
            cmd = self.get_create_group_command(i, combo['strategies'])
            if cmd:
                print(f"\n🔧 创建命令:")
                print(cmd)
            else:
                print(f"\n⚠️  无法生成创建命令（缺少 strategy_token）")
    
    def save_result(self, result: Dict, output_file: str):
        """保存结果到文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        self.log(f"\n💾 结果已保存: {output_file}")
    
    def get_create_group_command(self, combo_index: int, strategies: List[Dict]) -> Optional[str]:
        """生成创建策略组的命令"""
        tokens = []
        for s in strategies:
            token = s.get('strategy_token')
            if token:
                tokens.append(token)
            else:
                self.log(f"⚠️  策略 {s.get('name')} 缺少 strategy_token")
        
        if not tokens:
            return None
        
        combo_name = f"智能组合_{combo_index}_{datetime.now().strftime('%Y%m%d')}"
        tokens_str = ','.join(tokens)
        
        cmd = (
            f"python3 skills/backtest-query/query.py \\\n"
            f"  --create-group \\\n"
            f"  --group-name \"{combo_name}\" \\\n"
            f"  --strategy-tokens \"{tokens_str}\""
        )
        
        return cmd


# ==================== 主函数 ====================

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="智能分组推荐系统")
    
    # 查询需求
    parser.add_argument("--query", type=str, required=True, help="用户查询需求描述")
    
    # 数据查询参数（全局参数）
    parser.add_argument("--coins", type=str, help="币种列表（逗号分隔）")
    parser.add_argument("--strategy-types", type=str, help="策略类型列表（逗号分隔）")
    parser.add_argument("--directions", type=str, help="方向列表（逗号分隔）")
    parser.add_argument("--search-pcts", type=str, help="比例选择列表（逗号分隔）")
    parser.add_argument("--ai-time-ids", type=str, help="AI时间ID列表（逗号分隔）")
    parser.add_argument("--versions", type=str, help="策略版本列表（逗号分隔）")
    parser.add_argument("--search-recommand-type", type=int, default=1, help="推荐类型（1=推荐 2=交易中，默认=1）")
    
    # 映射参数（按策略/币种区分，优先级高于全局参数）
    parser.add_argument("--strategy-version-map", type=str, help='策略→版本映射（JSON格式）。格式: {"11": ["4.3", "4.4"], "7": null}')
    parser.add_argument("--strategy-direction-map", type=str, help='策略→方向映射（JSON格式）。格式: {"11": ["long", "short"], "7": ["long"]}')
    parser.add_argument("--coin-pct-map", type=str, help='币种→比例映射（JSON格式）。格式: {"BTC": ["80", "100"], "ETH": null}')
    
    # 分组和筛选参数
    parser.add_argument("--top-per-group", type=int, default=5, help="每种排序方式取几个策略")
    parser.add_argument("--max-combinations", type=int, default=10, help="最多推荐几个组合")
    parser.add_argument("--sort-methods", type=str, help="排序方式（逗号分隔）")
    parser.add_argument("--api-sort", type=int, choices=[1, 2, 3, 4], help="API排序类型（1=最新 2=收益 3=夏普 4=回撤，默认=2）")
    
    # 并行查询参数
    parser.add_argument("--max-workers", type=int, default=10, help="并发线程数（默认10）")
    parser.add_argument("--max-qps", type=int, default=20, help="每秒最大查询数（默认20）")
    parser.add_argument("--retry-times", type=int, default=3, help="查询失败重试次数（默认3）")
    parser.add_argument("--log-level", type=str, default="normal",
                       choices=["quiet", "normal", "detail"],
                       help="日志级别（quiet=静默/normal=正常/detail=详细，默认normal）")
    
    # 详情筛选条件
    parser.add_argument("--min-total-win-rate", type=float, help="最小总胜率")
    parser.add_argument("--min-recent-profit-rate", type=float, help="最小近期收益率")
    parser.add_argument("--max-recent-drawdown", type=float, help="最大近期回撤")
    parser.add_argument("--min-trade-count", type=int, help="最小交易次数")
    parser.add_argument("--min-stability", type=float, help="最小稳定性")
    
    # 输出参数
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    
    return parser.parse_args()


def main():
    """主函数"""
    # 1. 解析参数
    args = parse_arguments()
    
    # 2. 验证参数
    try:
        validate_args(args)
    except ValidationError as e:
        print(f"❌ 参数错误: {e}")
        sys.exit(1)
    
    # 3. 获取 token
    token = get_user_token()
    if not token:
        print("❌ 无法自动获取 token（当前 workspace 未关联用户）")
        sys.exit(1)
    
    # 4. 生成查询组合
    try:
        combinations = build_query_combinations(args, token)
    except Exception as e:
        print(f"❌ 生成查询组合失败: {e}")
        sys.exit(1)
    
    # 5. 构建基础查询参数
    base_params = {
        'token': token,
        'page': 1,
        'limit': -1,
        'search_recommand_type': args.search_recommand_type,
        'sort_type': args.api_sort if args.api_sort else 2  # 默认按收益排序
    }
    
    # 6. 并行批量查询
    try:
        executor = ParallelQueryExecutor(
            max_workers=args.max_workers,
            max_qps=args.max_qps,
            retry_times=args.retry_times,
            verbose=not args.quiet,
            log_level="quiet" if args.quiet else args.log_level
        )
        strategies = executor.batch_query_parallel(token, combinations, base_params)
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    if not strategies:
        print("❌ 未查询到任何策略")
        sys.exit(1)
    
    # 7. 构建筛选条件
    detail_criteria = build_detail_criteria(args)
    sort_methods = parse_csv(args.sort_methods) if args.sort_methods else None
    
    # 8. 智能推荐
    recommender = SmartGroupRecommender(token, verbose=not args.quiet)
    
    try:
        result = recommender.smart_recommend(
            query_text=args.query,
            strategies=strategies,
            top_per_group=args.top_per_group,
            detail_criteria=detail_criteria,
            max_combinations=args.max_combinations,
            sort_methods=sort_methods,
            api_sort_type=args.api_sort
        )
    except Exception as e:
        print(f"❌ 推荐失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 9. 输出结果
    recommender.print_result(result)
    if args.output:
        recommender.save_result(result, args.output)
    
    print("\n✅ 推荐完成")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 未预期错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
