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
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
from query import query_backtest, get_backtest_detail, get_version_info
from analysis import recommend_combinations


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
    """从当前 workspace 自动获取 token"""
    agent_id = None
    current = os.path.abspath(os.getcwd())
    
    while current != '/':
        basename = os.path.basename(current)
        if basename.startswith('clawd-'):
            agent_id = basename.replace('clawd-', '')
            break
        current = os.path.dirname(current)
    
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
    if args.version_configs:
        try:
            configs = json.loads(args.version_configs)
            if not isinstance(configs, list):
                raise ValidationError("--version-configs 必须是 JSON 数组格式")
            return configs
        except json.JSONDecodeError as e:
            raise ValidationError(f"--version-configs JSON 解析失败: {e}")
    return None


def build_query_combinations(args, token: str) -> List[Dict]:
    """
    根据参数生成查询组合（统一返回字典列表）
    
    Args:
        args: 命令行参数
        token: 用户 token（用于获取 version_info）
    
    Returns:
        [{'coin': 'BTC', 'strategy_type': 1, 'direction': 'long', 'version': '4.3', 'version_extra': {...}, ...}, ...]
    """
    # 解析所有参数
    coins = parse_csv(args.coins) or [None]
    strategy_types = parse_csv_int(args.strategy_types) or [None]
    directions = parse_csv(args.directions) or [None]
    search_pcts = parse_csv(args.search_pcts) or [None]
    ai_time_ids = parse_csv(args.ai_time_ids) or [None]
    
    combinations = []
    
    if args.version_configs:
        # 版本配置对象模式（version_configs 优先，忽略 versions）
        version_configs = json.loads(args.version_configs)
        
        for coin, st, direction, pct, time_id, vc in itertools.product(
            coins, strategy_types, directions, search_pcts, ai_time_ids, version_configs
        ):
            combo = {
                'coin': coin,
                'strategy_type': st,
                'direction': direction,
                'search_pct': pct,
                'ai_time_id': time_id,
                'version': vc.get('version'),  # 提取 version 字段
                'version_extra': vc  # 整个对象作为 version_extra
            }
            combinations.append(combo)
    else:
        # 传统模式：使用 versions 参数
        versions = parse_csv(args.versions) or [None]
        
        for coin, st, direction, pct, time_id, version in itertools.product(
            coins, strategy_types, directions, search_pcts, ai_time_ids, versions
        ):
            combo = {
                'coin': coin,
                'strategy_type': st,
                'direction': direction,
                'search_pct': pct,
                'ai_time_id': time_id,
                'version': version
            }
            
            # 如果指定了 version，需要调用 get_version_info 获取 version_extra
            if version and st:
                try:
                    version_extra = get_version_info(token, st, version)
                    if version_extra:
                        combo['version_extra'] = version_extra
                except Exception as e:
                    # 获取失败时跳过，不阻塞流程
                    print(f"⚠️  获取 version_info 失败 (strategy_type={st}, version={version}): {e}")
            
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


def batch_query_strategies(token: str, combinations: List[Dict], base_params: Dict, verbose: bool = True) -> List[Dict]:
    """
    批量查询策略并去重合并
    
    Args:
        token: 用户 token
        combinations: 查询参数组合列表
        base_params: 基础查询参数
        verbose: 是否输出详细信息
    
    Returns:
        合并去重后的策略列表
    """
    all_strategies = []
    seen_back_ids = set()
    
    # 参数映射（组合参数 → API 参数）
    param_mapping = {
        'coin': 'search_coin',
        'strategy_type': 'strategy_type',
        'direction': 'search_direction',
        'search_pct': 'search_pct',
        'ai_time_id': 'ai_time_id',
        'version': 'version',
        'version_extra': 'version_extra'  # 整个版本配置对象
    }
    
    if verbose:
        print(f"📋 共需查询 {len(combinations)} 个参数组合")
    
    for i, params in enumerate(combinations, 1):
        fetch_params = base_params.copy()
        
        # 应用参数映射
        for key, value in params.items():
            if value is not None and key in param_mapping:
                fetch_params[param_mapping[key]] = value
        
        if verbose:
            print(f"\n🔍 [{i}/{len(combinations)}] 查询: {format_params(params)}")
        
        try:
            result = query_backtest(**fetch_params)
            
            if "error" in result:
                if verbose:
                    print(f"   ⚠️  查询失败: {result['error']}")
                continue
            
            strategies = result.get("info", [])
            new_count = deduplicate_and_add(strategies, all_strategies, seen_back_ids)
            
            if verbose:
                print(f"   ✅ 获取 {len(strategies)} 条，新增 {new_count} 条（去重后）")
            
        except Exception as e:
            if verbose:
                print(f"   ⚠️  查询异常: {str(e)}")
            continue
    
    if verbose:
        print(f"\n📊 合并后共 {len(all_strategies)} 条策略")
    
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
        
        self.log(f"\n📊 获取详情数据（最多 {max_fetch} 个）...")
        
        for i, strategy in enumerate(strategies[:max_fetch], 1):
            back_id = strategy.get('back_id')
            if not back_id:
                self.log(f"   [{i}/{min(len(strategies), max_fetch)}] ⚠️  缺少 back_id，跳过")
                continue
            
            coin = strategy.get('coin', 'N/A')
            name = strategy.get('name', 'N/A')
            
            self.log(f"   [{i}/{min(len(strategies), max_fetch)}] {coin} / {name}")
            
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
                    self.log(f"      ⚠️  API返回错误: {detail['error']}，跳过该策略")
            except Exception as e:
                self.log(f"      ⚠️  获取异常: {str(e)}，跳过该策略")
                continue
        
        self.log(f"✅ 成功获取 {len(enriched)} 个策略详情")
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
        
        for method in sort_methods:
            self.log(f"   🔹 按 {method} 排序取 Top {top_n}")
            
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
            
            # 取前 N 个
            for strategy in sorted_list[:top_n]:
                back_id = strategy.get('back_id')
                if back_id and back_id not in selected:
                    selected[back_id] = strategy
                    self.log(f"      ✅ {strategy.get('coin')} / {strategy.get('name')} ({method})")
        
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
                "selected_strategies": all_selected,
                "combinations": []
            }
        
        self.log(f"\n🎲 生成策略组合（最多 {max_combinations} 个）...")
        
        # 构建偏好参数
        preferences = {}
        if detail_criteria:
            if 'max_recent_drawdown' in detail_criteria:
                preferences['max_drawdown'] = detail_criteria['max_recent_drawdown']
            # 可以根据其他筛选条件动态调整偏好
        
        combinations = recommend_combinations(
            strategies=all_selected,
            group_size=min(len(all_selected), 5),  # 组合大小默认5个策略
            top_n=max_combinations,
            preferences=preferences if preferences else None
        )
        
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
        
        print(f"\n🎯 分组维度: {' → '.join(result['group_by'])}")
        print(f"📦 分组数量: {len(result['groups'])} 组")
        print(f"🔄 排序方式: {', '.join(result.get('sort_methods', ['sharpe']))}")
        print(f"📊 总共获取: {result['total_fetched']} 条策略")
        print(f"✅ 筛选出: {result['total_selected']} 条优质策略")
        
        print(f"\n🌟 推荐组合: {len(result['combinations'])} 个")
        
        for i, combo in enumerate(result['combinations'][:5], 1):
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
    
    # 数据查询参数
    parser.add_argument("--coins", type=str, help="币种列表（逗号分隔）")
    parser.add_argument("--strategy-types", type=str, help="策略类型列表（逗号分隔）")
    parser.add_argument("--directions", type=str, help="方向列表（逗号分隔）")
    parser.add_argument("--search-pcts", type=str, help="比例选择列表（逗号分隔）")
    parser.add_argument("--ai-time-ids", type=str, help="AI时间ID列表（逗号分隔）")
    parser.add_argument("--versions", type=str, help="策略版本列表（逗号分隔）")
    parser.add_argument("--version-configs", type=str, help="版本配置对象数组（JSON格式）")
    parser.add_argument("--search-recommand-type", type=int, default=1, help="推荐类型（1=推荐 2=交易中，默认=1）")
    
    # 分组和筛选参数
    parser.add_argument("--top-per-group", type=int, default=5, help="每种排序方式取几个策略")
    parser.add_argument("--max-combinations", type=int, default=10, help="最多推荐几个组合")
    parser.add_argument("--sort-methods", type=str, help="排序方式（逗号分隔）")
    parser.add_argument("--api-sort", type=int, choices=[1, 2, 3, 4], help="API排序类型（1=最新 2=收益 3=夏普 4=回撤，默认=2）")
    
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
    
    # 6. 批量查询
    try:
        strategies = batch_query_strategies(token, combinations, base_params, verbose=not args.quiet)
    except Exception as e:
        print(f"❌ 查询失败: {e}")
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
