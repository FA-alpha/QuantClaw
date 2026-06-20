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
import atexit
import tempfile
import shutil
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed
from query import query_backtest, get_backtest_detail, get_version_info
from analysis import recommend_combinations

from qc_log import log_error, ErrorType

# ==================== JSONL 磁盘缓存 ====================

# 策略骨架字段：下游分组/排序/筛选/输出需要的轻量字段
# 对照 query.py format_result(json) + smart_group_recommend 实际从策略 dict 读取的字段
_SKELETON_FIELDS = frozenset([
    'back_id', 'id', 'name', 'coin', 'direction', 'strategy_type',
    'strategy_token', 'year_rate', 'sharp_rate', 'max_loss', 'win_rate',
    'score', 'version', 'leverage',
])

# 详情缓存目录（会话级，进程退出自动清理）
_DETAIL_CACHE_DIR = None


def _get_cache_dir() -> str:
    """获取当前会话的 JSONL 缓存目录（惰性创建）"""
    global _DETAIL_CACHE_DIR
    if _DETAIL_CACHE_DIR is None:
        _DETAIL_CACHE_DIR = tempfile.mkdtemp(prefix='backtest_cache_')
    return _DETAIL_CACHE_DIR


def _slim_strategy(strategy: Dict) -> Dict:
    """提取策略的骨架字段，丢弃大数组"""
    return {k: strategy.get(k) for k in _SKELETON_FIELDS if k in strategy}


def _load_strategy_by_back_id(back_id, cache_file: str) -> Optional[Dict]:
    """
    从 JSONL 缓存中按 back_id 查找完整策略数据。
    用于下游需要完整字段时按需回读。
    """
    if not os.path.exists(cache_file):
        return None
    with open(cache_file, 'r') as f:
        for line in f:
            s = json.loads(line)
            if s.get('back_id') == back_id:
                return s
    return None


def _cleanup_cache():
    """清理磁盘缓存"""
    global _DETAIL_CACHE_DIR
    if _DETAIL_CACHE_DIR and os.path.isdir(_DETAIL_CACHE_DIR):
        shutil.rmtree(_DETAIL_CACHE_DIR, ignore_errors=True)
        _DETAIL_CACHE_DIR = None


# 进程退出时自动清理
atexit.register(_cleanup_cache)


# ==================== 全局日志控制 ====================

def _should_print_warning() -> bool:
    """判断是否应该输出警告信息（可通过环境变量关闭）"""
    return os.environ.get('SUPPRESS_WARNINGS') != '1'


def _should_print_debug() -> bool:
    """判断是否应该输出 DEBUG 信息"""
    return os.environ.get('DEBUG_BACKTEST') == '1'


def _should_print_verbose() -> bool:
    """判断是否应该输出详细结果（默认简洁，节省token）"""
    return os.environ.get('VERBOSE_OUTPUT') == '1'


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

def get_user_token(agent_id: Optional[str] = None) -> Optional[str]:
    """
    从当前 workspace 自动获取 token
    
    Args:
        agent_id: 可选，显式指定 agent_id（推荐）
    
    支持两种情况：
    1. 显式传入 agent_id（最可靠）
    2. 从 PWD 路径中识别（软链接兼容）
    
    Returns:
        str: usertoken 或 None
    """
    # 如果未显式传入，尝试从路径识别
    if not agent_id:
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
    except Exception as e:
        log_error(
            error_msg=f"读取用户配置失败: {e}",
            exception=e,
            context={"function": "get_user_token", "agent_id": agent_id, "users_file": users_file},
            agent_id=agent_id
        )
    
    return None


# ==================== 参数处理 ====================

def validate_args(args):
    """统一参数验证"""
    # 映射参数验证在 build_query_combinations 中进行
    return None


def build_query_combinations(args, token: str, agent_id: str = None) -> List[Dict]:
    """
    根据参数生成查询组合（统一返回字典列表）
    
    参数优先级体系：
    1. 映射参数（最高优先级）：strategy-version-map, strategy-direction-map, coin-pct-map
    2. 全局参数（中优先级）：versions, directions, search-pcts
    3. 自动查询（最低优先级，需 --auto-expand）：未传参数时自动获取
    
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
            error_msg = f"--strategy-version-map JSON 解析失败: {e}"
            log_error(error_msg, error_type=ErrorType.PARSE, context={"input": args.strategy_version_map}, agent_id=agent_id)
            raise ValidationError(error_msg)
    
    if args.strategy_direction_map:
        try:
            strategy_direction_map = json.loads(args.strategy_direction_map)
        except json.JSONDecodeError as e:
            error_msg = f"--strategy-direction-map JSON 解析失败: {e}"
            log_error(error_msg, error_type=ErrorType.PARSE, context={"input": args.strategy_direction_map}, agent_id=agent_id)
            raise ValidationError(error_msg)
    
    if args.coin_pct_map:
        try:
            coin_pct_map = json.loads(args.coin_pct_map)
        except json.JSONDecodeError as e:
            error_msg = f"--coin-pct-map JSON 解析失败: {e}"
            log_error(error_msg, error_type=ErrorType.PARSE, context={"input": args.coin_pct_map}, agent_id=agent_id)
            raise ValidationError(error_msg)
    
    # ==================== 第1步：获取独立参数 ====================
    
    # 1. 币种列表
    if args.coins:
        coins = parse_csv(args.coins)
    elif args.auto_expand:
        # 自动扩展模式：查询所有币种
        result = get_coin_list(token, agent_id=agent_id)
        if "error" in result:
            if _should_print_warning():
                print(f"⚠️  获取币种列表失败: {result['error']}，使用默认值")
            coins = ["BTC", "ETH", "SOL"]
        else:
            coins = [c["coin"] for c in result.get("info", [])]
            if not coins:
                coins = ["BTC", "ETH", "SOL"]
    else:
        # 默认模式：没有指定则报错（引导用户确认）
        raise ValidationError("未指定币种参数。请先询问用户想查询哪些币种，可提示用户输入'列表'查看所有可用币种。")
    
    # 2. 策略类型列表
    if args.strategy_types:
        strategy_types = parse_csv_int(args.strategy_types)
    elif args.auto_expand:
        # 自动扩展模式：查询所有策略类型
        result = get_ai_strategy_list(token, agent_id=agent_id)
        if "error" in result:
            if _should_print_warning():
                print(f"⚠️  获取策略列表失败: {result['error']}，使用默认值")
            strategy_types = [11, 7, 1]
        else:
            strategy_types = [s["strategy_type"] for s in result.get("info", [])]
            if not strategy_types:
                strategy_types = [11, 7, 1]
    else:
        # 默认模式：没有指定则报错（引导用户确认）
        raise ValidationError("未指定策略类型参数。请先询问用户想查询哪种策略类型（如风霆、网格、趋势等），可提示用户输入'列表'查看所有策略类型。")
    
    # 3. 时间ID列表（可选参数，未提供则不限制时间）
    if args.ai_time_ids:
        ai_time_ids = parse_csv(args.ai_time_ids)
    elif args.auto_expand:
        # 自动扩展模式：查询所有时间ID
        result = get_ai_time_list(token, agent_id=agent_id)
        if "error" in result:
            if _should_print_warning():
                print(f"⚠️  获取时间列表失败: {result['error']}，使用默认值")
            ai_time_ids = ["5"]
        else:
            ai_time_ids = [str(t["id"]) for t in result.get("info", [])]
            if not ai_time_ids:
                ai_time_ids = ["5"]
    else:
        # 默认模式：时间为可选参数，未提供则不限制
        ai_time_ids = None
    
    # ==================== 第2步：获取策略完整信息（用于提取 versions） ====================
    
    strategy_info_map = {}  # {strategy_type: strategy_info}
    result = get_ai_strategy_list(token, agent_id=agent_id)
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
                # null → 根据 auto_expand 决定
                if args.auto_expand:
                    versions_list = auto_get_versions(st)
                else:
                    versions_list = [None]
            
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
        
        # ==================== 优先级3：自动查询或使用默认 ====================
        elif args.auto_expand:
            versions_list = auto_get_versions(st)
        else:
            # 默认模式：不指定版本（使用 None 表示不限制版本）
            versions_list = [None]
        
        # ==================== 获取该策略的 directions（优先级同上） ====================
        if str(st) in strategy_direction_map:
            direction_spec = strategy_direction_map[str(st)]
            
            if direction_spec is None:
                # null → 根据 auto_expand 决定
                if args.auto_expand:
                    directions = auto_get_directions(st)
                else:
                    directions = [None]
            elif isinstance(direction_spec, list):
                directions = direction_spec
            else:
                print(f"⚠️  策略 {st} 方向配置格式错误: {direction_spec}")
                directions = auto_get_directions(st)
        
        elif args.directions:
            directions = parse_csv(args.directions)
        
        elif args.auto_expand:
            directions = auto_get_directions(st)
        
        else:
            # 默认模式：不指定方向（使用 None 表示不限制方向）
            directions = [None]
        
        # === 嵌套循环：version → direction → coin → pct → time_id ===
        for version_item in versions_list:
            for direction in directions:
                for coin in coins:
                    # === 获取该币种的 search_pcts（优先级同上） ===
                    if coin in coin_pct_map:
                        pct_spec = coin_pct_map[coin]
                        
                        if pct_spec is None:
                            # null → 根据 auto_expand 决定
                            if args.auto_expand:
                                search_pcts = auto_get_pcts(coin)
                            else:
                                search_pcts = [None]
                        elif isinstance(pct_spec, list):
                            search_pcts = pct_spec
                        else:
                            print(f"⚠️  币种 {coin} 比例配置格式错误: {pct_spec}")
                            search_pcts = auto_get_pcts(coin)
                    
                    elif args.search_pcts:
                        search_pcts = parse_csv(args.search_pcts)
                    
                    elif args.auto_expand:
                        search_pcts = auto_get_pcts(coin)
                    
                    else:
                        # 默认模式：不指定比例（使用 None 表示不限制比例）
                        search_pcts = [None]
                    
                    for pct in search_pcts:
                        # 处理时间ID（可能为 None）
                        time_id_list = ai_time_ids if ai_time_ids else [None]
                        
                        for time_id in time_id_list:
                            # === 构建组合（只添加非 None 的字段）===
                            combo = {
                                'coin': coin,
                                'strategy_type': st,
                            }
                            
                            # 方向（可选）
                            if direction is not None:
                                combo['direction'] = direction
                            
                            # 比例（可选）
                            if pct is not None:
                                combo['search_pct'] = pct
                            
                            # 时间ID（可选）
                            if time_id is not None:
                                combo['ai_time_id'] = time_id
                            
                            # 处理版本信息
                            if version_item is not None and isinstance(version_item, dict):
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
        seen_strategies = {}  # {back_id: strategy} 用于更新已存在的策略
        failed_count = 0
        failed_details = []  # 记录失败详情
        
        # JSONL 磁盘缓存：完整数据落盘，内存只保留骨架
        _jsonl_path = os.path.join(_get_cache_dir(), 'strategies.jsonl')
        _jsonl_fp = open(_jsonl_path, 'w')
        
        if self.verbose and self.log_level != "quiet":
            print(f"\n🚀 开始并行查询 {total} 个组合...", flush=True)
            print(f"   并发: {self.max_workers} 线程, 限流: {self.max_qps} QPS", flush=True)
            print(f"   预计耗时: ~{total / self.max_qps:.0f} 秒\n", flush=True)
        
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
        
        # 准备查询参数列表（同时保留原始 combo 用于后续同步）
        query_params_list = []
        combo_metadata_list = []  # 保存每个查询的元数据
        
        for combo in combinations:
            params = base_params.copy()
            for key, value in combo.items():
                if value is not None and key in param_mapping:
                    params[param_mapping[key]] = value
            query_params_list.append(params)
            combo_metadata_list.append(combo)  # 保存原始 combo
        
        # 并行执行
        completed = 0
        milestone_interval = max(1, min(10, total // 10))  # 每10%或至少每10个，避免长时间无输出
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            if self.verbose and self.log_level != "quiet":
                print(f"   任务已提交，开始查询...", flush=True)
            
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
                        
                        # 从对应的 combo metadata 中同步字段到策略数据
                        combo_meta = combo_metadata_list[idx]
                        direction = combo_meta.get('direction')
                        coin = combo_meta.get('coin')
                        
                        # DEBUG
                        if os.environ.get('DEBUG_SYNC') == '1':
                            print(f"[DEBUG] Combo #{idx}: direction={direction}, coin={coin}, strategies={len(strategies)}")
                        
                        for s in strategies:
                            # 同步 direction（如果 API 没返回）
                            if not s.get('direction') and direction:
                                s['direction'] = direction
                            # 同步 coin（确保一致）
                            if not s.get('coin') and coin:
                                s['coin'] = coin
                        
                        # ✅ 去重后：完整数据落盘 JSONL，内存只保留骨架
                        for s in strategies:
                            back_id = s.get('back_id')
                            if not back_id:
                                continue
                            if back_id not in seen_back_ids:
                                seen_back_ids.add(back_id)
                                _jsonl_fp.write(json.dumps(s, ensure_ascii=False) + '\n')
                                slim_s = _slim_strategy(s)
                                all_strategies.append(slim_s)
                                seen_strategies[back_id] = slim_s
                            else:
                                # 已存在：只更新 direction（不覆盖已有数据）
                                existing = seen_strategies.get(back_id)
                                if existing and not existing.get('direction') and s.get('direction'):
                                    existing['direction'] = s.get('direction')
                
                except Exception as e:
                    failed_count += 1
                    failed_details.append(f"#{idx+1}: {e}")
                    # 只在 detail 模式输出每个异常
                    if self.verbose and self.log_level == "detail":
                        print(f"❌ 组合 #{idx+1} 异常: {e}")
                
                # 里程碑输出
                if self.verbose and self.log_level == "normal" and completed % milestone_interval == 0:
                    progress = completed / total * 100
                    print(f"   进度: {progress:.0f}% ({completed}/{total})", flush=True)
        
        # 关闭 JSONL 缓存文件
        _jsonl_fp.close()
        
        if self.verbose and self.log_level != "quiet":
            print(f"\n✅ 查询完成:", flush=True)
            print(f"   成功: {total - failed_count}/{total}", flush=True)
            print(f"   失败: {failed_count}", flush=True)
            print(f"   策略数: {len(all_strategies)} (去重后)", flush=True)
            print(f"   缓存: {_jsonl_path}", flush=True)
            
            # 失败率过高时给出提示
            if failed_count > total * 0.3:
                print(f"\n⚠️  失败率过高 ({failed_count}/{total} = {failed_count/total*100:.1f}%)", flush=True)
                print(f"   建议: 降低 --max-qps 或检查网络连接", flush=True)
                # detail 模式才显示前几个失败原因
                if self.log_level == "detail" and failed_details:
                    print(f"   前5个失败原因:", flush=True)
                    for detail in failed_details[:5]:
                        print(f"     - {detail}", flush=True)
            print(flush=True)
        
        return all_strategies


# ==================== 推荐器类 ====================

class SmartGroupRecommender:
    """智能分组推荐器"""
    
    def __init__(self, token: str, verbose: bool = True, agent_id: str = None):
        self.token = token
        self.verbose = verbose
        self.agent_id = agent_id
    
    def log(self, msg: str):
        if self.verbose:
            print(msg)
    
    # ==================== 智能分组策略 ====================
    
    def infer_grouping_from_intent(self, intent: Dict) -> List[str]:
        """
        根据 AI 意图分析结果推断分组策略
        
        Args:
            intent: AI 意图分析 JSON
        
        Returns:
            分组维度列表
        """
        strategy_goal = intent.get('strategy_goal', 'unknown')
        constraints = intent.get('constraints', {})
        preferences = intent.get('preferences', {})
        
        dimensions = []
        
        # 根据策略目标决定分组
        if strategy_goal == 'hedging':
            # 对冲：优先按方向分组，再按币种
            diversity_priority = preferences.get('diversity_priority', 'direction')
            if diversity_priority == 'direction':
                dimensions = ['direction', 'coin']
            else:
                dimensions = ['coin', 'direction']
        
        elif strategy_goal == 'diversification':
            # 分散：按币种分组（同方向多样化）
            dimensions = ['coin']
        
        elif strategy_goal == 'trend':
            # 趋势：单方向，按策略类型或币种分组
            diversity_priority = preferences.get('diversity_priority', 'strategy_type')
            if diversity_priority == 'coin':
                dimensions = ['coin']
            else:
                dimensions = ['strategy_type']
        
        else:  # unknown 或其他
            # 默认按币种分组
            dimensions = ['coin']
        
        return dimensions
    
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
                value = strategy.get(dim)
                
                # 如果关键维度为空，跳过该策略（不强制归类）
                if value is None:
                    if dim in ['direction', 'coin']:  # 关键维度
                        break  # 跳过这个策略
                    value = 'UNKNOWN'
                
                key_parts.append(str(value))
            else:
                # 只有成功构造完整 key 才加入分组
                key = tuple(key_parts)
                if key not in groups:
                    groups[key] = []
                groups[key].append(strategy)
        
        return groups
    
    def _create_strategy_summary(self, strategies: List[Dict]) -> Dict:
        """
        创建策略列表的精简摘要（避免输出大量数据）
        
        Args:
            strategies: 策略列表
        
        Returns:
            精简摘要字典
        """
        summary = {
            "total_count": len(strategies),
            "by_coin": {},
            "by_direction": {},
            "by_coin_direction": {},
            "sample_strategies": []  # 只保留前3个作为样本
        }
        
        for s in strategies:
            coin = s.get('coin', 'UNKNOWN')
            direction = s.get('direction', 'UNKNOWN')
            
            # 按币种统计
            summary["by_coin"][coin] = summary["by_coin"].get(coin, 0) + 1
            
            # 按方向统计
            summary["by_direction"][direction] = summary["by_direction"].get(direction, 0) + 1
            
            # 按币种+方向统计
            key = f"{coin}_{direction}"
            summary["by_coin_direction"][key] = summary["by_coin_direction"].get(key, 0) + 1
        
        # 保留前3个策略作为样本（只保留关键字段）
        for s in strategies[:3]:
            summary["sample_strategies"].append({
                "id": s.get("id"),
                "back_id": s.get("back_id"),
                "coin": s.get("coin"),
                "direction": s.get("direction"),
                "name": s.get("name"),
                "strategy_token": s.get("strategy_token"),
                "year_rate": s.get("year_rate"),
                "sharp_rate": s.get("sharp_rate"),
                "max_loss": s.get("max_loss")
            })
        
        return summary
    
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
                detail = get_backtest_detail(self.token, back_id, agent_id=self.agent_id)
                
                if "error" not in detail:
                    # 提取关键详情指标
                    # 🚫 不存 time_line_list / coin_fee_list (全项目 0 次读取，单纯占内存)
                    info = detail.get('info', {})
                    strategy['_detail'] = {
                        'total_stat': info.get('total_stat', {}),
                        'recent_stat': info.get('recent_stat', {}),
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
    
    def _single_strategy_recommend(
        self,
        strategies: List[Dict],
        intent: Dict,
        detail_criteria: Optional[Dict] = None,
        api_sort_type: Optional[int] = None
    ) -> Dict:
        """
        单策略推荐模式 - 不进行组合分析，直接返回排序后的策略列表
        
        Args:
            strategies: 查询到的策略列表
            intent: 意图分析结果
            detail_criteria: 详情筛选条件
            api_sort_type: API排序类型
            
        Returns:
            包含单条策略列表的结果
        """
        self.log("\n🔍 开始单策略推荐...")
        
        # 1. 获取数量要求
        constraints = intent.get('constraints', {})
        limit = constraints.get('min_strategies', 5)
        
        self.log(f"📊 候选策略数: {len(strategies)}")
        self.log(f"🎯 返回数量: {limit}")
        
        # 2. 按收益率排序（或使用API指定的排序）
        sort_key = 'year_rate'  # 默认按收益率
        if api_sort_type == 3:
            sort_key = 'sharp_rate'
        elif api_sort_type == 4:
            sort_key = 'max_loss'
            
        self.log(f"📈 排序字段: {sort_key}")
        
        sorted_strategies = sorted(
            strategies,
            key=lambda x: float(x.get(sort_key, 0) or 0),
            reverse=(sort_key != 'max_loss')  # 回撤越小越好
        )
        
        # 3. 取前N个
        selected = sorted_strategies[:limit]
        
        self.log(f"✅ 已选择 {len(selected)} 个策略")
        
        # 4. 构建返回结果
        result = {
            "mode": "single_strategy",
            "strategies": strategies,
            "total_fetched": len(strategies),
            "total_selected": len(selected),
            'selected_strategies':selected,
            "sort_by": sort_key
        }
        
        return result
    
    def smart_recommend(
        self,
        query_text: str,
        strategies: List[Dict],
        top_per_group: int = 5,
        detail_criteria: Optional[Dict] = None,
        max_combinations: int = 10,
        sort_methods: Optional[List[str]] = None,
        api_sort_type: Optional[int] = None,
        intent: Optional[Dict] = None
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
            intent: AI 意图分析结果（可选）
        
        Returns:
            推荐结果
        """
        self.log("="*70)
        self.log("🧠 智能分组推荐系统")
        self.log("="*70)
        
        # 0. 检查是否是单策略推荐模式
        if intent and intent.get('strategy_goal') == 'single_strategy':
            self.log(f"\n📝 用户需求: {query_text}")
            self.log("🎯 单策略推荐模式 - 跳过组合分析")
            return self._single_strategy_recommend(
                strategies=strategies,
                intent=intent,
                detail_criteria=detail_criteria,
                api_sort_type=api_sort_type
            )
        
        # 1. 推断分组策略（考虑 intent）
        self.log(f"\n📝 用户需求: {query_text}")
        
        # 读取 min_strategies 约束（如果有）
        min_strategies = 3  # 默认值
        coin_strategies_count = None  # 按币种指定数量（可选）
        group_strategies_count = None  # 按分组键指定数量（可选）
        
        if intent:
            constraints = intent.get('constraints', {})
            min_strategies = constraints.get('min_strategies', 3)
            coin_strategies_count = constraints.get('coin_strategies_count')
            group_strategies_count = constraints.get('group_strategies_count')
            # 验证一致性（优先级：group_strategies_count > coin_strategies_count）
            if group_strategies_count:
                expected_total = sum(group_strategies_count.values())
                if expected_total != min_strategies:
                    self.log(f"⚠️  警告: group_strategies_count 总数({expected_total}) ≠ min_strategies({min_strategies})")
                    self.log(f"   将使用 group_strategies_count 总数: {expected_total}")
                    min_strategies = expected_total
            elif coin_strategies_count:
                # 检查是否在"同币种多空对冲"场景误用
                strategy_goal = intent.get('strategy_goal')
                diversity_priority = intent.get('preferences', {}).get('diversity_priority')
                
                # 只在同币种多空对冲时警告（diversity_priority == 'direction'）
                if strategy_goal == 'hedging' and diversity_priority == 'direction':
                    self.log(f"⚠️  警告: 同币种多空对冲不建议使用 coin_strategies_count")
                    self.log(f"   建议: 使用 group_strategies_count 精确控制多空比例")
                    self.log(f"   或不指定，让对冲算法自动平衡")
                
                # 跨币种对冲（diversity_priority == 'coin'）使用 coin_strategies_count 是合理的
                
                expected_total = sum(coin_strategies_count.values())
                if expected_total != min_strategies:
                    self.log(f"⚠️  警告: coin_strategies_count 总数({expected_total}) ≠ min_strategies({min_strategies})")
                    self.log(f"   将使用 coin_strategies_count 总数: {expected_total}")
                    min_strategies = expected_total
            
            # 使用 AI 意图调整分组策略
            group_by = self.infer_grouping_from_intent(intent)
            self.log(f"🎯 分组策略（基于意图 {intent.get('strategy_goal')}）: {' → '.join(group_by)}")
            self.log(f"🎯 最少策略数要求: {min_strategies}")
        else:
            # 原有逻辑
            group_by = self.infer_grouping_strategy(query_text)
            self.log(f"🎯 分组策略: {' → '.join(group_by)}")
        
        # 动态调整 top_per_group（确保候选池足够）
        original_top_per_group = top_per_group
        if min_strategies > top_per_group * 2:
            # 如果需要的策略数超过候选池可能的大小，自动扩展
            top_per_group = (min_strategies + 1) // 2 + 1
            self.log(f"📈 自动调整 top_per_group: {original_top_per_group} → {top_per_group}")
            self.log(f"   原因: min_strategies={min_strategies} 需要更大的候选池")
        
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
        
        # 读取策略数量配置（支持两种方式）
        coin_strategies_count = None
        group_strategies_count = None
        if intent:
            constraints = intent.get('constraints', {})
            coin_strategies_count = constraints.get('coin_strategies_count')
            group_strategies_count = constraints.get('group_strategies_count')
        
        if group_strategies_count:
            self.log(f"\n🎯 按分组键指定数量筛选策略:")
            for key, count in group_strategies_count.items():
                self.log(f"   {key}: {count} 个")
        elif coin_strategies_count:
            self.log(f"\n🎯 按币种指定数量筛选策略:")
            for coin, count in coin_strategies_count.items():
                self.log(f"   {coin}: {count} 个")
        elif sort_methods:
            self.log(f"\n🎯 每组按多种排序方式筛选策略...")
            self.log(f"   排序方式: {', '.join(sort_methods)}")
            self.log(f"   每种方式取 Top {top_per_group}")
        else:
            self.log(f"\n🎯 每组按默认方式筛选 Top {top_per_group} 策略...")
        
        for key, group_strategies in groups.items():
            label = " / ".join([f"{val}" for val in key])
            self.log(f"\n--- {label} ({len(group_strategies)} 个策略) ---")
            
            # 确定该组要取几个策略
            # 优先级：group_strategies_count > coin_strategies_count > top_per_group
            current_top_n = top_per_group
            
            # 方式1：按完整分组键匹配（最精确）
            if group_strategies_count:
                group_key = "_".join(str(v) for v in key)
                if group_key in group_strategies_count:
                    current_top_n = group_strategies_count[group_key]
                    self.log(f"   使用指定数量: {current_top_n} 个（来自 group_strategies_count[{group_key}]）")
            
            # 方式2：按币种匹配（需要特殊处理多维度分组）
            elif coin_strategies_count and 'coin' in group_by:
                coin_index = group_by.index('coin')
                coin = key[coin_index]
                if coin in coin_strategies_count:
                    # 检查是否是多维度分组（如 coin + direction）
                    if len(group_by) > 1:
                        # 多维度分组（如对冲模式）：扩大候选池，让后续算法决定
                        # 取 coin_strategies_count 的 2-3 倍作为候选池
                        current_top_n = max(top_per_group, coin_strategies_count[coin] * 2)
                        self.log(f"   扩大候选池: {current_top_n} 个（{coin} 总需求 {coin_strategies_count[coin]} 个，多维度分组）")
                    else:
                        # 单维度分组（纯按币种）：直接使用指定数量
                        current_top_n = coin_strategies_count[coin]
                        self.log(f"   使用指定数量: {current_top_n} 个（来自 coin_strategies_count[{coin}]）")
            
            top_strategies = self.get_top_by_multiple_sorts(group_strategies, top_n=current_top_n, sort_methods=sort_methods)
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
        
        # 5. 检查候选策略数量是否足够
        if len(all_selected) < 2:
            self.log("⚠️  策略数量不足，无法形成组合")
            return {
                "error": "候选策略不足",
                "message": "未找到足够的策略来生成组合",
                "suggestions": [
                    "降低筛选条件（如胜率、回撤要求）"
                ],
                "query": query_text,
                "total_fetched": len(strategies),
                "total_selected": len(all_selected),
                "selected_summary": self._create_strategy_summary(all_selected)
            }
        
        # 检查是否满足 min_strategies 要求
        if len(all_selected) < min_strategies:
            self.log(f"⚠️  候选策略数量（{len(all_selected)}）< 最少策略数要求（{min_strategies}）")
            return {
                "error": "候选策略不足以满足 min_strategies 要求",
                "message": f"找到 {len(all_selected)} 个策略，但需要至少 {min_strategies} 个",
                "suggestions": [
                    f"降低 min_strategies 要求（当前={min_strategies}，建议≤{len(all_selected)}）",
                    "移除版本或方向限制"
                ],
                "query": query_text,
                "total_fetched": len(strategies),
                "total_selected": len(all_selected),
                "min_strategies_required": min_strategies,
                "selected_summary": self._create_strategy_summary(all_selected)
            }
        
        self.log(f"\n🎲 生成策略组合（最多 {max_combinations} 个）...")
        
        # 构建偏好参数
        preferences = {}
        if detail_criteria:
            if 'max_recent_drawdown' in detail_criteria:
                preferences['max_drawdown'] = detail_criteria['max_recent_drawdown']
            # 可以根据其他筛选条件动态调整偏好
        
        # 分支：根据 intent 决定组合生成方式
        all_combinations = []
        n_strategies = len(all_selected)
        
        if intent:
            strategy_goal = intent.get('strategy_goal')
            constraints = intent.get('constraints', {})
            preferences_intent = intent.get('preferences', {})
            diversity_priority = preferences_intent.get('diversity_priority')
            
            # 将 diversity_priority 和 min_strategies 传递给 preferences
            if diversity_priority:
                preferences['diversity_priority'] = diversity_priority
            
            # 读取 min_strategies 约束
            min_strategies = constraints.get('min_strategies', 2)
            preferences['min_strategies'] = min_strategies
            
            # 传递 constraints（包含 coins 等硬约束）
            preferences['constraints'] = constraints
            
            if strategy_goal == 'hedging':
                # 对冲模式：强制多空平衡
                hedge_type = "跨币种对冲" if diversity_priority == 'coin' else "同币种多空"
                self.log(f"🎯 对冲模式：生成{hedge_type}组合（最少{min_strategies}个策略）")
                all_combinations = self._generate_hedging_combinations(
                    all_selected, groups, group_by, max_combinations, preferences
                )
            
            elif strategy_goal == 'diversification' and diversity_priority == 'strategy_type':
                # 策略类型分散模式
                self.log(f"🎯 策略类型分散模式：生成多策略组合")
                all_combinations = self._generate_strategy_type_combinations(
                    all_selected, groups, group_by, max_combinations, preferences
                )
            
            else:
                # 其他意图：使用默认模式
                all_combinations = self._generate_default_combinations(
                    all_selected, max_combinations, preferences
                )
        else:
            # 默认模式：使用原有逻辑（向后兼容）
            all_combinations = self._generate_default_combinations(
                all_selected, max_combinations, preferences
            )
        
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
            "selected_summary": self._create_strategy_summary(all_selected),
            "combinations": combinations,
            "criteria": detail_criteria,
            "sort_methods": sort_methods if sort_methods else ['sharpe', 'return', 'drawdown']
        }
    
    def _generate_default_combinations(self, all_selected: List[Dict], max_combinations: int, preferences: Dict) -> List[Dict]:
        """默认组合生成逻辑（原有逻辑）"""
        all_combinations = []
        n_strategies = len(all_selected)
        
        # 获取最少策略数量要求
        min_strategies = preferences.get('min_strategies', 3)
        
        # 根据策略数量决定组合大小（尊重 min_strategies）
        if n_strategies >= 7:
            # 策略充足：生成3种大小（保守、稳健、激进）
            sizes = [max(3, min_strategies), 5, 7]
        elif n_strategies >= 5:
            # 策略中等：生成2种大小
            sizes = [max(3, min_strategies), 5]
        elif n_strategies >= 3:
            # 策略较少：生成1-2种大小
            sizes = [max(3, min_strategies, n_strategies - 1), n_strategies - 2] if n_strategies > 4 else [max(3, min_strategies)]
        else:
            # 策略太少，使用全部
            sizes = [n_strategies]
        
        # 过滤掉超出可用策略数的大小
        sizes = [s for s in sizes if s <= n_strategies]
        if not sizes:
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
        
        return all_combinations
    
    def _generate_hedging_combinations(
        self, 
        all_selected: List[Dict], 
        groups: Dict, 
        group_by: List[str],
        max_combinations: int,
        preferences: Dict
    ) -> List[Dict]:
        """
        对冲模式组合生成：强制多空平衡
        
        Args:
            all_selected: 所有筛选后的策略
            groups: 分组结果
            group_by: 分组维度
            max_combinations: 最多生成几个组合
            preferences: 偏好参数（包含 diversity_priority）
        
        Returns:
            对冲组合列表
        """
        # 找出 long 和 short 分组
        long_strategies = []
        short_strategies = []
        
        for key, group_strategies in groups.items():
            # key 是 tuple，例如 ('long', 'BTC') 或 ('short', 'SOL')
            direction_idx = group_by.index('direction') if 'direction' in group_by else -1
            
            if direction_idx >= 0:
                direction = key[direction_idx]
                if direction == 'long':
                    long_strategies.extend(group_strategies)
                elif direction == 'short':
                    short_strategies.extend(group_strategies)
        
        self.log(f"   做多策略: {len(long_strategies)} 个")
        self.log(f"   做空策略: {len(short_strategies)} 个")
        
        if not long_strategies or not short_strategies:
            self.log(f"⚠️  缺少多空策略，降级为默认模式")
            return self._generate_default_combinations(all_selected, max_combinations, preferences)
        
        # 检查是否需要跨币种对冲
        diversity_priority = preferences.get('diversity_priority', 'direction')
        require_different_coins = (diversity_priority == 'coin')
        
        # 获取最少策略数量要求
        min_strategies = preferences.get('min_strategies', 2)
        
        if require_different_coins:
            # 统计涉及的币种数量
            all_coins = set(s['coin'] for s in all_selected)
            if len(all_coins) > 1:
                self.log(f"   跨币种对冲模式：强制不同币种 ({', '.join(all_coins)})")
            else:
                self.log(f"   ⚠️  只有单个币种，无法跨币种对冲，降级为同币种多空")
                require_different_coins = False
        
        # 生成对冲组合：从 long 和 short 中各取部分
        all_combinations = []
        
        # 根据 min_strategies 决定组合策略
        if min_strategies <= 2:
            # 策略1：简单对冲（1 long + 1 short = 2个策略）
            self.log(f"   生成简单对冲组合（2个策略）")
            
            if require_different_coins:
                # 跨币种对冲：按币种分组后各取一个
                from collections import defaultdict
                long_by_coin = defaultdict(list)
                short_by_coin = defaultdict(list)
                
                for s in long_strategies:
                    long_by_coin[s['coin']].append(s)
                for s in short_strategies:
                    short_by_coin[s['coin']].append(s)
                
                self.log(f"   Long 币种: {list(long_by_coin.keys())}")
                self.log(f"   Short 币种: {list(short_by_coin.keys())}")
                
                # 跨币种配对
                for long_coin, long_list in long_by_coin.items():
                    for short_coin, short_list in short_by_coin.items():
                        if long_coin == short_coin:
                            continue  # 跳过同币种
                        
                        # 从每个币种中取前2个
                        for l_strat in long_list[:2]:
                            for s_strat in short_list[:2]:
                                combo_strategies = [l_strat, s_strat]
                                combos = recommend_combinations(
                                    strategies=combo_strategies,
                                    group_size=2,
                                    top_n=1,
                                    preferences=preferences
                                )
                                for combo in combos:
                                    combo['style'] = '跨币种对冲'
                                    combo['hedging_type'] = 'simple'
                                all_combinations.extend(combos)
                                
                                if len(all_combinations) >= max_combinations * 3:
                                    break
                            if len(all_combinations) >= max_combinations * 3:
                                break
                        if len(all_combinations) >= max_combinations * 3:
                            break
                    if len(all_combinations) >= max_combinations * 3:
                        break
            else:
                # 同币种对冲：直接取前N个
                for l_strat in long_strategies[:3]:
                    for s_strat in short_strategies[:3]:
                        combo_strategies = [l_strat, s_strat]
                        combos = recommend_combinations(
                            strategies=combo_strategies,
                            group_size=2,
                            top_n=1,
                            preferences=preferences
                        )
                        for combo in combos:
                            combo['style'] = '对冲型'
                            combo['hedging_type'] = 'simple'
                        all_combinations.extend(combos)
        
        # 策略2：强化对冲（2 long + 2 short = 4个策略）
        if min_strategies >= 4 and len(long_strategies) >= 2 and len(short_strategies) >= 2:
            self.log(f"   生成强化对冲组合（4个策略）")
            import itertools
            
            if require_different_coins:
                # 跨币种对冲：从每个币种中分别取
                from collections import defaultdict
                long_by_coin = defaultdict(list)
                short_by_coin = defaultdict(list)
                
                for s in long_strategies:
                    long_by_coin[s['coin']].append(s)
                for s in short_strategies:
                    short_by_coin[s['coin']].append(s)
                
                # 确保至少有2个币种
                if len(long_by_coin) >= 2 or len(short_by_coin) >= 2:
                    # 尝试构建包含多个币种的组合
                    for long_coins in itertools.combinations(list(long_by_coin.keys()), min(2, len(long_by_coin))):
                        for short_coins in itertools.combinations(list(short_by_coin.keys()), min(2, len(short_by_coin))):
                            # 从每个选定的币种中取一个策略
                            long_combo = [long_by_coin[c][0] for c in long_coins]
                            short_combo = [short_by_coin[c][0] for c in short_coins]
                            
                            # 确保币种不完全重叠
                            all_coins_in_combo = set(s['coin'] for s in long_combo + short_combo)
                            if len(all_coins_in_combo) == 1:
                                continue
                            
                            combo_strategies = long_combo + short_combo
                            if len(combo_strategies) >= 4:
                                combos = recommend_combinations(
                                    strategies=combo_strategies[:4],
                                    group_size=4,
                                    top_n=1,
                                    preferences=preferences
                                )
                                for combo in combos:
                                    combo['style'] = '稳健对冲'
                                    combo['hedging_type'] = 'balanced'
                                all_combinations.extend(combos)
                                
                                if len(all_combinations) >= max_combinations * 3:
                                    break
                        if len(all_combinations) >= max_combinations * 3:
                            break
            else:
                # 同币种对冲：直接组合
                for long_pair in itertools.combinations(long_strategies[:5], 2):
                    for short_pair in itertools.combinations(short_strategies[:5], 2):
                        combo_strategies = list(long_pair) + list(short_pair)
                        combos = recommend_combinations(
                            strategies=combo_strategies,
                            group_size=4,
                            top_n=1,
                            preferences=preferences
                        )
                        for combo in combos:
                            combo['style'] = '稳健对冲'
                            combo['hedging_type'] = 'balanced'
                        all_combinations.extend(combos)
                        
                        if len(all_combinations) >= max_combinations * 3:
                            break
                    if len(all_combinations) >= max_combinations * 3:
                        break
        
        # 策略3：自定义数量对冲（min_strategies = 3, 5, 6等）
        if min_strategies == 3 or min_strategies > 4:
            self.log(f"   生成自定义对冲组合（{min_strategies}个策略）")
            import itertools
            
            # 计算 long 和 short 的分配（尽量平衡）
            long_count = min_strategies // 2
            short_count = min_strategies - long_count
            
            if len(long_strategies) >= long_count and len(short_strategies) >= short_count:
                if require_different_coins:
                    # 跨币种：按币种分组选择
                    from collections import defaultdict
                    long_by_coin = defaultdict(list)
                    short_by_coin = defaultdict(list)
                    
                    for s in long_strategies:
                        long_by_coin[s['coin']].append(s)
                    for s in short_strategies:
                        short_by_coin[s['coin']].append(s)
                    
                    # 从多个币种中选择
                    for long_coins in itertools.combinations(list(long_by_coin.keys()), min(long_count, len(long_by_coin))):
                        for short_coins in itertools.combinations(list(short_by_coin.keys()), min(short_count, len(short_by_coin))):
                            # 检查币种不完全相同
                            all_coins_in_combo = set(long_coins) | set(short_coins)
                            if len(all_coins_in_combo) == 1:
                                continue
                            
                            # 从每个币种中取一个策略
                            long_combo = [long_by_coin[c][0] for c in long_coins]
                            short_combo = [short_by_coin[c][0] for c in short_coins]
                            
                            combo_strategies = long_combo + short_combo
                            if len(combo_strategies) >= min_strategies:
                                combos = recommend_combinations(
                                    strategies=combo_strategies[:min_strategies],
                                    group_size=min_strategies,
                                    top_n=1,
                                    preferences=preferences
                                )
                                for combo in combos:
                                    combo['style'] = f'{min_strategies}策略对冲'
                                    combo['hedging_type'] = 'custom'
                                all_combinations.extend(combos)
                                
                                if len(all_combinations) >= max_combinations * 3:
                                    break
                        if len(all_combinations) >= max_combinations * 3:
                            break
                else:
                    # 同币种：直接组合
                    for long_combo in itertools.combinations(long_strategies[:6], long_count):
                        for short_combo in itertools.combinations(short_strategies[:6], short_count):
                            combo_strategies = list(long_combo) + list(short_combo)
                            combos = recommend_combinations(
                                strategies=combo_strategies,
                                group_size=min_strategies,
                                top_n=1,
                                preferences=preferences
                            )
                            for combo in combos:
                                combo['style'] = f'{min_strategies}策略对冲'
                                combo['hedging_type'] = 'custom'
                            all_combinations.extend(combos)
                            
                            if len(all_combinations) >= max_combinations * 3:
                                break
                        if len(all_combinations) >= max_combinations * 3:
                            break
            else:
                self.log(f"   ⚠️  策略数量不足（需要{long_count}多+{short_count}空），降级为简单对冲")
        
        return all_combinations
    
    def _generate_strategy_type_combinations(
        self,
        all_selected: List[Dict],
        groups: Dict,
        group_by: List[str],
        max_combinations: int,
        preferences: Dict
    ) -> List[Dict]:
        """
        策略类型分散模式：从不同策略类型中各取策略
        
        Args:
            all_selected: 所有筛选后的策略
            groups: 分组结果
            group_by: 分组维度
            max_combinations: 最多生成几个组合
            preferences: 偏好参数
        
        Returns:
            策略类型分散组合列表
        """
        # 按 strategy_type 分组
        type_groups = {}
        for strategy in all_selected:
            st = strategy.get('strategy_type', 'UNKNOWN')
            if st not in type_groups:
                type_groups[st] = []
            type_groups[st].append(strategy)
        
        # 获取最少策略数量要求
        min_strategies = preferences.get('min_strategies', 2)
        
        self.log(f"   策略类型数: {len(type_groups)}，最少策略数: {min_strategies}")
        for st, strategies in type_groups.items():
            self.log(f"   - 类型 {st}: {len(strategies)} 个策略")
        
        if len(type_groups) < 2:
            self.log(f"⚠️  策略类型不足2种，降级为默认模式")
            return self._generate_default_combinations(all_selected, max_combinations, preferences)
        
        # 生成组合：从每个类型中取策略
        all_combinations = []
        import itertools
        
        # 计算每个类型取几个策略
        num_types = len(type_groups)
        strategies_per_type = max(1, min_strategies // num_types)
        
        # 策略1：每个类型取 strategies_per_type 个
        type_list = list(type_groups.keys())
        for combo_types in itertools.combinations(type_list, min(len(type_list), max(2, num_types))):
            # 从每个类型中取策略
            type_strategy_lists = [type_groups[t][:3] for t in combo_types]
            
            for type_strategies in itertools.product(*type_strategy_lists):
                combo_strategies = list(type_strategies)
                
                # 检查是否满足最少策略数量
                if len(combo_strategies) < min_strategies:
                    continue
                
                combos = recommend_combinations(
                    strategies=combo_strategies,
                    group_size=len(combo_strategies),
                    top_n=1,
                    preferences=preferences
                )
                for combo in combos:
                    combo['style'] = '多策略型'
                    combo['diversity_type'] = 'strategy_type'
                    combo['strategy_types'] = list(combo_types)
                all_combinations.extend(combos)
                
                # 限制组合数量
                if len(all_combinations) >= max_combinations * 5:
                    break
            if len(all_combinations) >= max_combinations * 5:
                break
        
        return all_combinations
    
    def print_result(self, result: Dict):
        """打印推荐结果（简洁模式，节省token）"""
        if "error" in result:
            print(f"\n❌ 错误: {result['error']}")
            if "message" in result:
                print(f"   {result['message']}")
            if "suggestions" in result:
                print(f"\n💡 建议：")
                for i, suggestion in enumerate(result['suggestions'], 1):
                    print(f"   {i}. {suggestion}")
            return
        
        # 单策略推荐模式
        if result.get('mode') == 'single_strategy':
            print("\n" + "="*70)
            print("📊 单策略推荐结果")
            print("="*70)
            print(f"查询: {result.get('total_fetched', 0)} → 已选: {result.get('total_selected', 0)} 个")
            print(f"排序字段: {result.get('sort_by', 'year_rate')}")
            
            strategies = result.get('strategies', [])
            if strategies:
                print(f"\n🌟 推荐策略（Top {len(strategies)}）:")
                for i, s in enumerate(strategies, 1):
                    print(
                        f"  #{i} {s.get('name', 'N/A')} | "
                        f"收益{s.get('year_rate', 0)}% | "
                        f"夏普{s.get('sharp_rate', 0)} | "
                        f"回撤{s.get('max_loss', 0)}%"
                    )
                    print(f"      Token: {s.get('strategy_token', 'N/A')}")
            
            print(f"\n💡 提示:")
            print(f"   • 保存单个策略: query.py --add-strategy --strategy-token <token>")
            print(f"   • 创建策略组: query.py --create-group --strategy-tokens <t1,t2,...>")
            return
        
        # 组合推荐模式
        print("\n" + "="*70)
        print("📊 推荐结果")
        print("="*70)
        
        # 关键统计（一行）
        print(f"查询: {result.get('total_fetched', 0)} → 筛选: {result.get('total_selected', 0)} → 组合: {len(result.get('combinations', []))} 个")
        
        combinations = result.get('combinations', [])
        if not combinations:
            print("   （无推荐组合）")
            return
        
        # 只输出组合摘要，不输出详细策略列表（节省token）
        print(f"\n🌟 推荐组合（前3个）:")
        for i, combo in enumerate(combinations[:3], 1):
            style = combo.get('style', '')
            print(
                f"  #{i} [{style}] "
                f"评分{combo['score']:.1f} | "
                f"收益{combo['expected_return']:.1f}% | "
                f"回撤{combo['portfolio_risk']['max_drawdown']:.1f}% | "
                f"{len(combo['strategies'])}策略"
            )
        
        # 提示：完整数据在 JSON 输出中
        print(f"\n💡 提示: 完整策略详情和创建命令见 JSON 输出或使用 --output 保存")
    
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
    
    # Agent 认证
    parser.add_argument("--agent-id", type=str, help="Agent ID（可选，用于 token 自动获取）")
    
    # 意图分析（由 AI Agent 提供）
    parser.add_argument("--intent-json", type=str, help="意图分析 JSON（可选，由 AI Agent 预生成）")
    
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
    
    # 行为开关
    parser.add_argument("--auto-expand", action="store_true", 
                       help="自动扩展模式：未传参数时自动查询所有可能值（默认关闭）")
    
    return parser.parse_args()


def main():
    """主函数"""
    # 1. 解析参数
    args = parse_arguments()
    
    # 2. 解析意图 JSON（如果提供）
    intent = None
    if args.intent_json:
        try:
            intent = json.loads(args.intent_json)
            print(f"📋 使用 AI 意图分析: {intent.get('strategy_goal', 'unknown')}")
        except json.JSONDecodeError as e:
            print(f"⚠️  意图 JSON 解析失败: {e}，将使用默认逻辑")
            intent = None
    
    # 3. 验证参数
    try:
        validate_args(args)
    except ValidationError as e:
        # 记录验证错误
        log_error(
            error_msg=str(e),
            error_type=ErrorType.VALIDATION,
            context={"script": "smart_group_recommend.py", "args": vars(args)},
            agent_id=args.agent_id
        )
        
        error_result = {
            "error": "参数验证失败",
            "message": str(e),
            "suggestions": ["检查参数格式是否正确", "参考 SKILL.md 中的参数说明"]
        }
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(error_result, f, ensure_ascii=False, indent=2)
        else:
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)
    
    # 4. 获取 token
    token = get_user_token(agent_id=args.agent_id)
    if not token:
        error_result = {
            "error": "无法获取用户 token",
            "message": "未找到有效的用户认证",
            "suggestions": [
                "确保使用 --agent-id 参数",
                "检查 ~/.quantclaw/users.json 是否存在",
                "确认当前 agent 已注册"
            ]
        }
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(error_result, f, ensure_ascii=False, indent=2)
        else:
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)
    
    # 4. 生成查询组合
    try:
        combinations = build_query_combinations(args, token, agent_id=args.agent_id)
    except Exception as e:
        # 根据错误信息生成用户友好的建议
        error_msg = str(e)
        suggestions = []
        
        if "未指定币种" in error_msg or "币种" in error_msg:
            suggestions.append("请告诉我您想查询哪些币种（如 BTC、ETH 等）")
            suggestions.append("如果不确定，可以输入'列表'查看所有可用币种")
        
        if "未指定策略类型" in error_msg or "策略类型" in error_msg:
            suggestions.append("请告诉我您想查询哪种策略类型（如风霆、网格、趋势等）")
            suggestions.append("如果不确定，可以输入'列表'查看所有策略类型")
        
        if not suggestions:
            # 其他错误，使用通用建议
            suggestions = [
                "请检查输入的币种或策略类型是否正确",
                "您可以输入'列表'查看所有可用的选项"
            ]
        
        error_result = {
            "error": "参数不完整",
            "message": error_msg,
            "suggestions": suggestions
        }
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(error_result, f, ensure_ascii=False, indent=2)
        else:
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)
    
    # 5. 构建基础查询参数
    base_params = {
        'token': token,
        'page': 1,
        'limit': -1,
        'search_recommand_type': args.search_recommand_type,
        'sort_type': args.api_sort if args.api_sort else 2,  # 默认按收益排序
        'agent_id': args.agent_id  # 传递 agent_id
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
        error_result = {
            "error": "批量查询失败",
            "message": str(e),
            "suggestions": [
                "检查网络连接",
                "降低并发参数（--max-workers 或 --max-qps）",
                "检查 API 是否可用"
            ]
        }
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(error_result, f, ensure_ascii=False, indent=2)
        else:
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)
    
    if not strategies:
        error_result = {
            "error": "未查询到任何策略",
            "message": "查询参数未匹配到任何策略数据",
            "suggestions": [
                "检查时间范围是否有数据",
                "使用 query.py --list-coins 确认币种是否存在"
            ],
            "total_fetched": 0
        }
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(error_result, f, ensure_ascii=False, indent=2)
        else:
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)
    
    # 7. 构建筛选条件
    detail_criteria = build_detail_criteria(args)
    sort_methods = parse_csv(args.sort_methods) if args.sort_methods else None
    
    # 8. 智能推荐
    recommender = SmartGroupRecommender(token, verbose=not args.quiet, agent_id=args.agent_id)
    
    try:
        result = recommender.smart_recommend(
            query_text=args.query,
            strategies=strategies,
            top_per_group=args.top_per_group,
            detail_criteria=detail_criteria,
            max_combinations=args.max_combinations,
            sort_methods=sort_methods,
            api_sort_type=args.api_sort,
            intent=intent  # 传递 intent
        )
    except Exception as e:
        error_result = {
            "error": "推荐流程失败",
            "message": str(e),
            "suggestions": [
                "检查策略数据完整性",
                "降低 min_strategies 要求",
                "联系技术支持"
            ]
        }
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(error_result, f, ensure_ascii=False, indent=2)
        else:
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 9. 输出结果
    if not args.quiet:
        recommender.print_result(result)
    
    # 保存到文件（JSON 完整输出）
    if args.output:
        recommender.save_result(result, args.output)
        if not args.quiet:
            print(f"\n💾 完整结果已保存: {args.output}")
    
    if not args.quiet:
        print("\n✅ 推荐完成")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        error_result = {
            "error": "用户中断",
            "message": "执行被用户中断"
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)
    except Exception as e:
        # 记录错误日志
        log_error(
            error_msg=str(e),
            exception=e,
            context={"script": "smart_group_recommend.py", "args": sys.argv[1:]},
            agent_id=getattr(args, 'agent_id', None) if 'args' in locals() else None
        )
        
        error_result = {
            "error": "未预期错误",
            "message": str(e),
            "suggestions": ["联系技术支持", "查看完整错误日志"]
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        import traceback
        traceback.print_exc()
        sys.exit(1)
