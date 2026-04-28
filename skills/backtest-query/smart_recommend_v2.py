#!/usr/bin/env python3
"""
智能策略组合推荐 v2
接口优化版本：只传已知参数，接口返回全量数据，代码按需分类
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from query import query_backtest, get_backtest_detail, get_ai_strategy_list
from defaults import DefaultParams
from analysis import recommend_combinations


class SmartRecommenderV2:
    """智能推荐器 v2 - 接口优化版"""
    
    def __init__(self, token: str, verbose: bool = True):
        self.token = token
        self.verbose = verbose
        self.defaults = DefaultParams(token, verbose)
        
    def log(self, msg: str):
        """输出日志"""
        if self.verbose:
            print(msg)
    
    def _identify_loop_dimensions(
        self,
        coins: Optional[List[str]],
        strategy_type: Optional[int],
        direction: Optional[str],
        ai_time_id: Optional[str],
        year: Optional[int]
    ) -> Dict[str, any]:
        """
        识别需要循环的维度
        
        返回格式：
        {
            'coins': ['BTC', 'SOL'],  # None 表示不循环
            'directions': ['long', 'short'],
            'fixed_params': {
                'strategy_type': 11,
                'ai_time_id': '5'
            }
        }
        """
        loop_dims = {
            'coins': None,
            'directions': None,
            'fixed_params': {}
        }
        
        # 1. 币种维度
        if coins and len(coins) > 1:
            # 多个币种，需要循环
            loop_dims['coins'] = coins
            self.log(f"🔄 币种维度循环: {coins}")
        elif coins and len(coins) == 1:
            # 单个币种，固定参数
            loop_dims['fixed_params']['search_coin'] = coins[0]
            self.log(f"📌 币种固定: {coins[0]}")
        else:
            # 未指定，不传参数（接口返回全部）
            self.log(f"🌐 币种未指定，查询全部")
        
        # 2. 方向维度
        if direction:
            # 指定了方向，固定参数
            loop_dims['fixed_params']['search_direction'] = direction
            self.log(f"📌 方向固定: {direction}")
        else:
            # 未指定，检查是否需要循环
            # 对于对冲场景："BTC和SOL对冲" → 需要 long + short 组合
            if coins and len(coins) > 1:
                # 多币种对冲，需要循环方向
                loop_dims['directions'] = ['long', 'short']
                self.log(f"🔄 方向维度循环（对冲场景）: long + short")
            else:
                # 单币种或未指定，不传参数
                self.log(f"🌐 方向未指定，查询全部")
        
        # 3. 策略类型（固定参数）
        if strategy_type is not None:
            loop_dims['fixed_params']['strategy_type'] = strategy_type
            self.log(f"📌 策略类型固定: {strategy_type}")
        
        # 4. 时间（固定参数）
        if ai_time_id:
            loop_dims['fixed_params']['ai_time_id'] = ai_time_id
            self.log(f"📌 时间ID固定: {ai_time_id}")
        elif year:
            loop_dims['fixed_params']['search_year'] = year
            self.log(f"📌 年份固定: {year}")
        
        return loop_dims
    
    def _build_query_params(self, base_params: dict, loop_values: dict) -> dict:
        """
        构建查询参数
        
        Args:
            base_params: 基础固定参数
            loop_values: 当前循环的参数值 {'coin': 'BTC', 'direction': 'long'}
        """
        params = {
            'token': self.token,
            'page': 1,
            'limit': -1,  # 获取全部
            'sort_type': 2,  # 按收益率排序
            'search_recommand_type': 1,  # 推荐策略
            **base_params
        }
        
        # 添加循环参数
        if 'coin' in loop_values:
            params['search_coin'] = loop_values['coin']
        if 'direction' in loop_values:
            params['search_direction'] = loop_values['direction']
        
        return params
    
    def _classify_strategies(
        self, 
        raw_data: List[Dict],
        group_by: List[str]  # ['coin', 'direction', 'strategy_type']
    ) -> Dict[Tuple, List[Dict]]:
        """
        按指定维度对策略数据进行分类
        
        Args:
            raw_data: 接口返回的原始数据
            group_by: 分组维度列表
        
        Returns:
            分类后的数据 {('BTC', 'long', 11): [strategy1, strategy2, ...]}
        """
        classified = {}
        
        for strategy in raw_data:
            # 构建分组键
            key_parts = []
            for dim in group_by:
                if dim == 'coin':
                    key_parts.append(strategy.get('coin', 'UNKNOWN'))
                elif dim == 'direction':
                    key_parts.append(strategy.get('direction', 'UNKNOWN'))
                elif dim == 'strategy_type':
                    key_parts.append(strategy.get('strategy_type', 'UNKNOWN'))
                elif dim == 'ai_time_id':
                    key_parts.append(strategy.get('ai_time_id', 'UNKNOWN'))
            
            key = tuple(key_parts)
            
            if key not in classified:
                classified[key] = []
            classified[key].append(strategy)
        
        return classified
    
    def fetch_strategies(
        self,
        coins: Optional[List[str]] = None,
        amt_type: int = 2,
        sort_type: int = 2,
        strategy_type: Optional[int] = None,
        direction: Optional[str] = None,
        year: Optional[int] = None,
        ai_time_id: Optional[str] = None,
        recommand_type: int = 1,
        limit: int = 10,
        min_sharpe: Optional[float] = None,
        max_drawdown: Optional[float] = None
    ) -> List[Dict]:
        """
        查询并筛选策略（v2版本）
        
        核心逻辑：
        1. 识别需要循环的维度（coins + directions）
        2. 对于需要循环的维度，逐一查询
        3. 对于未指定的维度，不传参数（接口返回全部）
        4. 获取全量数据后，按需分类
        """
        self.log("\n" + "="*60)
        self.log("🚀 智能推荐 v2 - 接口优化版")
        self.log("="*60)
        
        # 1. 识别循环维度
        loop_config = self._identify_loop_dimensions(
            coins, strategy_type, direction, ai_time_id, year
        )
        
        # 2. 准备查询
        all_strategies = []
        query_count = 0
        
        # 3. 构建查询循环
        coins_to_query = loop_config['coins'] or [None]
        directions_to_query = loop_config['directions'] or [None]
        
        total_queries = len(coins_to_query) * len(directions_to_query)
        
        if total_queries > 1:
            self.log(f"\n📊 预计查询次数: {total_queries}")
            self.log(f"   - 币种: {len(coins_to_query)}")
            self.log(f"   - 方向: {len(directions_to_query)}")
        else:
            self.log(f"\n📊 单次查询（接口返回全量数据）")
        
        self.log("")
        
        # 4. 执行查询
        for coin in coins_to_query:
            for dir_ in directions_to_query:
                query_count += 1
                
                # 构建查询参数
                loop_values = {}
                if coin:
                    loop_values['coin'] = coin
                if dir_:
                    loop_values['direction'] = dir_
                
                params = self._build_query_params(
                    loop_config['fixed_params'],
                    loop_values
                )
                
                # 构建日志标签
                label_parts = []
                if coin:
                    label_parts.append(f"币种={coin}")
                if dir_:
                    label_parts.append(f"方向={dir_}")
                if strategy_type:
                    label_parts.append(f"策略={strategy_type}")
                if ai_time_id:
                    label_parts.append(f"时间={ai_time_id}")
                elif year:
                    label_parts.append(f"年份={year}")
                
                label = " / ".join(label_parts) if label_parts else "全部数据"
                
                self.log(f"🔍 [{query_count}/{total_queries}] 查询: {label}")
                
                # 调用接口
                result = query_backtest(**params)
                
                if "error" in result:
                    self.log(f"⚠️  查询失败: {result['error']}")
                    continue
                
                strategies = result.get("info", [])
                self.log(f"✅ 返回 {len(strategies)} 条数据")
                
                all_strategies.extend(strategies)
        
        # 5. 数据分类和统计
        self.log(f"\n📦 总计获取: {len(all_strategies)} 条策略数据")
        
        if all_strategies:
            # 统计维度分布
            coins_found = set(s.get('coin') for s in all_strategies)
            directions_found = set(s.get('direction') for s in all_strategies)
            strategy_types_found = set(s.get('strategy_type') for s in all_strategies)
            
            self.log(f"   - 币种: {len(coins_found)} 个 {sorted(coins_found)}")
            self.log(f"   - 方向: {len(directions_found)} 个 {sorted(directions_found)}")
            self.log(f"   - 策略类型: {len(strategy_types_found)} 个 {sorted(strategy_types_found)}")
        
        # 6. 筛选
        if min_sharpe or max_drawdown:
            before = len(all_strategies)
            
            filtered = []
            for s in all_strategies:
                if min_sharpe and s.get("sharp_rate", 0) < min_sharpe:
                    continue
                if max_drawdown and s.get("max_loss", 100) > max_drawdown:
                    continue
                filtered.append(s)
            
            all_strategies = filtered
            self.log(f"\n🔽 筛选后剩余: {len(all_strategies)}/{before} 条")
        
        return all_strategies
    
    def enrich_with_details(self, strategies: List[Dict], max_fetch: int = 20) -> List[Dict]:
        """获取策略详情"""
        self.log(f"\n📊 获取策略详情（最多 {max_fetch} 个）...")
        
        enriched = []
        for i, strategy in enumerate(strategies[:max_fetch], 1):
            back_id = strategy.get("back_id")
            if not back_id:
                continue
            
            self.log(f"   [{i}/{min(len(strategies), max_fetch)}] 获取 {strategy.get('coin')} / {strategy.get('name')} 详情...")
            
            detail = get_backtest_detail(self.token, back_id)
            if "error" not in detail:
                strategy['_detail'] = detail.get('info', {})
                enriched.append(strategy)
            else:
                self.log(f"      ⚠️  获取失败: {detail['error']}")
        
        return enriched
    
    def save_to_memory(self, result: dict, workspace: str):
        """保存分析结果到 memory"""
        memory_dir = os.path.join(workspace, "memory", "analysis")
        os.makedirs(memory_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recommend_{timestamp}.json"
        filepath = os.path.join(memory_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        self.log(f"\n💾 结果已保存: {filepath}")
        return filepath


def main():
    parser = argparse.ArgumentParser(description="智能策略组合推荐 v2")
    
    # 基础参数
    parser.add_argument("--coins", type=str, help="币种列表（逗号分隔），如 'BTC,ETH'")
    parser.add_argument("--strategy-type", type=int, help="策略类型")
    parser.add_argument("--direction", type=str, choices=['long', 'short'], help="方向")
    parser.add_argument("--year", type=int, help="年份")
    parser.add_argument("--ai-time-id", type=str, help="时间ID")
    
    # 筛选参数
    parser.add_argument("--min-sharpe", type=float, help="最小夏普率")
    parser.add_argument("--max-drawdown", type=float, help="最大回撤")
    parser.add_argument("--top-n", type=int, default=10, help="推荐前N个策略")
    
    # 输出参数
    parser.add_argument("--workspace", type=str, default=os.getcwd(), help="工作区路径")
    parser.add_argument("--save-memory", action="store_true", help="保存到 memory")
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
    
    # 处理币种参数
    coins = None
    if args.coins:
        coins = [c.strip() for c in args.coins.split(',')]
    
    # 创建推荐器
    recommender = SmartRecommenderV2(token, verbose=not args.quiet)
    
    try:
        # 查询策略
        strategies = recommender.fetch_strategies(
            coins=coins,
            strategy_type=args.strategy_type,
            direction=args.direction,
            year=args.year,
            ai_time_id=args.ai_time_id,
            min_sharpe=args.min_sharpe,
            max_drawdown=args.max_drawdown
        )
        
        if not strategies:
            print("❌ 未找到符合条件的策略")
            sys.exit(1)
        
        # 获取详情
        enriched = recommender.enrich_with_details(strategies, max_fetch=20)
        
        # 推荐组合
        print("\n" + "="*60)
        print("🎯 智能推荐组合")
        print("="*60)
        
        combinations = recommend_combinations(
            enriched,
            max_combinations=args.top_n,
            min_sharpe=args.min_sharpe,
            max_drawdown=args.max_drawdown
        )
        
        if args.save_memory:
            result = {
                "timestamp": datetime.now().isoformat(),
                "query": {
                    "coins": coins,
                    "strategy_type": args.strategy_type,
                    "direction": args.direction,
                    "year": args.year,
                    "ai_time_id": args.ai_time_id
                },
                "strategies": strategies,
                "combinations": combinations
            }
            recommender.save_to_memory(result, args.workspace)
        
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
