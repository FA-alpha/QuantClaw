#!/usr/bin/env python3
"""
智能分组推荐系统
根据用户需求智能分组，每组筛选优质策略，基于详情数据深度分析后形成最优组合
"""

import sys
import os
import json
import argparse
from typing import List, Dict, Optional, Tuple, Callable
from datetime import datetime
from query import query_backtest, get_backtest_detail
from analysis import recommend_combinations


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
        
        示例:
            "帮我找BTC和ETH的多空策略" → ['coin', 'direction']
            "不同周期的网格策略" → ['ai_time_id', 'strategy_type']
            "各个币种的最优策略" → ['coin']
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
    
    def classify_strategies(
        self,
        strategies: List[Dict],
        group_by: List[str]
    ) -> Dict[Tuple, List[Dict]]:
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
                continue
            
            coin = strategy.get('coin', 'N/A')
            name = strategy.get('name', 'N/A')
            
            self.log(f"   [{i}/{min(len(strategies), max_fetch)}] {coin} / {name}")
            
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
                self.log(f"      ⚠️  获取失败: {detail['error']}")
        
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
            'total_profit_rate': total_stat.get('profit_rate', 0),  # 总收益率
            'total_win_rate': total_stat.get('win_rate', 0),  # 总胜率
            'total_trade_count': total_stat.get('trade_count', 0),  # 总交易次数
            'total_max_drawdown': total_stat.get('max_loss', 100),  # 总最大回撤
            
            # 近期指标（recent_stat）
            'recent_profit_rate': recent_stat.get('profit_rate', 0),  # 近期收益率
            'recent_win_rate': recent_stat.get('win_rate', 0),  # 近期胜率
            'recent_trade_count': recent_stat.get('trade_count', 0),  # 近期交易次数
            'recent_max_drawdown': recent_stat.get('max_loss', 100),  # 近期最大回撤
        }
        
        # 计算稳定性指标
        if metrics['total_profit_rate'] > 0:
            # 近期表现 vs 总体表现
            metrics['recent_stability'] = metrics['recent_profit_rate'] / metrics['total_profit_rate']
        else:
            metrics['recent_stability'] = 0
        
        return metrics
    
    def filter_by_detail_criteria(
        self,
        strategies: List[Dict],
        criteria: Dict[str, any]
    ) -> List[Dict]:
        """
        基于详情指标筛选策略
        
        Args:
            strategies: 包含详情的策略列表
            criteria: 筛选条件
                {
                    'min_total_win_rate': 60,  # 总胜率 >= 60%
                    'min_recent_profit_rate': 10,  # 近期收益 >= 10%
                    'max_recent_drawdown': 15,  # 近期回撤 <= 15%
                    'min_trade_count': 50,  # 总交易次数 >= 50
                    'min_stability': 0.8  # 稳定性 >= 0.8
                }
        
        Returns:
            筛选后的策略列表
        """
        filtered = []
        
        for strategy in strategies:
            metrics = self.analyze_detail_metrics(strategy)
            
            # 应用筛选条件
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
            sort_methods: 排序方式列表，支持：
                - 'sharpe': 夏普率（默认）
                - 'return': 年化收益率
                - 'drawdown': 最小回撤
                - 'win_rate': 胜率（需详情）
                - 'stability': 稳定性（需详情）
                - 'score': 综合评分（如果数据中有）
                - 'custom:字段名': 自定义字段排序
        
        Returns:
            去重后的策略列表
        """
        if not sort_methods:
            sort_methods = ['sharpe', 'return', 'drawdown']
        
        selected = {}  # 用 back_id 去重
        
        for method in sort_methods:
            self.log(f"   🔹 按 {method} 排序取 Top {top_n}")
            
            if method == 'sharpe':
                sorted_list = sorted(
                    strategies,
                    key=lambda s: s.get('sharp_rate', 0),
                    reverse=True
                )
            elif method == 'return':
                sorted_list = sorted(
                    strategies,
                    key=lambda s: s.get('year_rate', 0),
                    reverse=True
                )
            elif method == 'drawdown':
                sorted_list = sorted(
                    strategies,
                    key=lambda s: s.get('max_loss', 100),
                    reverse=False  # 回撤越小越好
                )
            elif method == 'win_rate':
                # 需要详情数据
                sorted_list = sorted(
                    strategies,
                    key=lambda s: s.get('_metrics', {}).get('total_win_rate', 0),
                    reverse=True
                )
            elif method == 'stability':
                # 需要详情数据
                sorted_list = sorted(
                    strategies,
                    key=lambda s: s.get('_metrics', {}).get('recent_stability', 0),
                    reverse=True
                )
            elif method == 'score':
                # 综合评分（支持多种字段名）
                sorted_list = sorted(
                    strategies,
                    key=lambda s: (
                        s.get('score', 0) or 
                        s.get('total_score', 0) or
                        s.get('recommend_score', 0) or
                        s.get('rating', 0)
                    ),
                    reverse=True
                )
            elif method.startswith('custom:'):
                # 自定义字段排序
                field_name = method.split(':', 1)[1]
                sorted_list = sorted(
                    strategies,
                    key=lambda s: s.get(field_name, 0),
                    reverse=True
                )
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
        fetch_params: Dict,
        top_per_group: int = 5,
        detail_criteria: Optional[Dict] = None,
        max_combinations: int = 10,
        sort_methods: Optional[List[str]] = None
    ) -> Dict:
        """
        智能推荐主流程
        
        Args:
            query_text: 用户查询需求
            fetch_params: 数据查询参数
            top_per_group: 每组取几个策略
            detail_criteria: 详情筛选条件
            max_combinations: 最多推荐几个组合
            sort_methods: 排序方式列表 ['sharpe', 'return', 'drawdown', ...]
        
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
        
        # 2. 查询数据
        self.log(f"\n🔍 查询策略数据...")
        result = query_backtest(**fetch_params)
        
        if "error" in result:
            return {"error": result["error"]}
        
        strategies = result.get("info", [])
        self.log(f"✅ 获取 {len(strategies)} 条策略")
        
        if not strategies:
            return {"error": "未找到策略"}
        
        # 3. 分组
        groups = self.classify_strategies(strategies, group_by)
        self.log(f"\n📦 分组结果: {len(groups)} 组")
        
        # 打印分组统计
        for key, group_strategies in groups.items():
            label = " / ".join([f"{dim}={val}" for dim, val in zip(group_by, key)])
            self.log(f"   - {label}: {len(group_strategies)} 个策略")
        
        # 4. 每组按多种排序方式筛选 top 策略
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
            
            # 使用多种排序方式取 Top-N
            top_strategies = self.get_top_by_multiple_sorts(
                group_strategies,
                top_n=top_per_group,
                sort_methods=sort_methods
            )
            
            self.log(f"📊 去重后选择 {len(top_strategies)} 个策略")
            
            # 获取详情
            self.log(f"\n📊 获取详情数据...")
            enriched = self.fetch_detail_data(top_strategies, max_fetch=len(top_strategies))
            
            # 基于详情进一步筛选
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
        combinations = recommend_combinations(
            all_selected,
            max_combinations=max_combinations,
            min_sharpe=None,
            max_drawdown=None
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
    
    def save_result(self, result: Dict, output_file: str):
        """保存结果到文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        self.log(f"\n💾 结果已保存: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="智能分组推荐系统")
    
    # 查询需求
    parser.add_argument("--query", type=str, required=True, help="用户查询需求描述")
    
    # 数据查询参数
    parser.add_argument("--coins", type=str, help="币种列表（逗号分隔）")
    parser.add_argument("--strategy-types", type=str, help="策略类型列表（逗号分隔）")
    parser.add_argument("--directions", type=str, help="方向列表（逗号分隔）")
    
    # 分组和筛选参数
    parser.add_argument("--top-per-group", type=int, default=5, help="每种排序方式取几个策略")
    parser.add_argument("--max-combinations", type=int, default=10, help="最多推荐几个组合")
    parser.add_argument("--sort-methods", type=str, help="排序方式（逗号分隔），支持: sharpe,return,drawdown,win_rate,stability,score,custom:字段名")
    
    # 详情筛选条件
    parser.add_argument("--min-total-win-rate", type=float, help="最小总胜率")
    parser.add_argument("--min-recent-profit-rate", type=float, help="最小近期收益率")
    parser.add_argument("--max-recent-drawdown", type=float, help="最大近期回撤")
    parser.add_argument("--min-trade-count", type=int, help="最小交易次数")
    parser.add_argument("--min-stability", type=float, help="最小稳定性（近期/总体）")
    
    # 输出参数
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    
    args = parser.parse_args()
    
    # 获取 token
    try:
        users_file = os.path.expanduser("~/.quantclaw/users.json")
        with open(users_file, 'r') as f:
            users = json.load(f)
            current_user = users.get("current_user")
            if not current_user:
                print("❌ 未找到当前用户")
                sys.exit(1)
            token = users["users"][current_user]["token"]
    except Exception as e:
        print(f"❌ 获取 token 失败: {e}")
        sys.exit(1)
    
    # 构建查询参数
    fetch_params = {
        'token': token,
        'page': 1,
        'limit': -1,
        'sort_type': 2,
        'search_recommand_type': 1
    }
    
    if args.coins:
        # 如果指定了多个币种，需要分别查询
        # 这里简化处理，只传第一个
        coins = [c.strip() for c in args.coins.split(',')]
        if len(coins) == 1:
            fetch_params['search_coin'] = coins[0]
    
    if args.strategy_types:
        types = [int(t.strip()) for t in args.strategy_types.split(',')]
        if len(types) == 1:
            fetch_params['strategy_type'] = types[0]
    
    if args.directions:
        dirs = [d.strip() for d in args.directions.split(',')]
        if len(dirs) == 1:
            fetch_params['search_direction'] = dirs[0]
    
    # 构建详情筛选条件
    detail_criteria = {}
    if args.min_total_win_rate:
        detail_criteria['min_total_win_rate'] = args.min_total_win_rate
    if args.min_recent_profit_rate:
        detail_criteria['min_recent_profit_rate'] = args.min_recent_profit_rate
    if args.max_recent_drawdown:
        detail_criteria['max_recent_drawdown'] = args.max_recent_drawdown
    if args.min_trade_count:
        detail_criteria['min_trade_count'] = args.min_trade_count
    if args.min_stability:
        detail_criteria['min_stability'] = args.min_stability
    
    # 处理排序方式
    sort_methods = None
    if args.sort_methods:
        sort_methods = [m.strip() for m in args.sort_methods.split(',')]
    
    # 创建推荐器
    recommender = SmartGroupRecommender(token, verbose=not args.quiet)
    
    try:
        # 执行智能推荐
        result = recommender.smart_recommend(
            query_text=args.query,
            fetch_params=fetch_params,
            top_per_group=args.top_per_group,
            detail_criteria=detail_criteria if detail_criteria else None,
            max_combinations=args.max_combinations,
            sort_methods=sort_methods
        )
        
        # 打印结果
        recommender.print_result(result)
        
        # 保存结果
        if args.output:
            recommender.save_result(result, args.output)
        
        print("\n✅ 推荐完成")
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
