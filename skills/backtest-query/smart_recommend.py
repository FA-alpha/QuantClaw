#!/usr/bin/env python3
"""
智能策略组合推荐
Agent 调用此脚本进行完整的分析和推荐
"""

import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict, Optional
from query import query_backtest, get_backtest_detail, get_ai_strategy_list
from defaults import DefaultParams
from analysis import recommend_combinations


class SmartRecommender:
    """智能推荐器"""
    
    def __init__(self, token: str, verbose: bool = True):
        self.token = token
        self.verbose = verbose
        # 使用统一的默认参数管理器
        self.defaults = DefaultParams(token, verbose)
        self._strategy_versions_cache = {}  # 缓存策略版本信息
        
    def log(self, msg: str):
        """输出日志"""
        if self.verbose:
            print(msg)
    
    def get_strategy_versions(self, strategy_type: int) -> List[Dict]:
        """
        获取指定策略类型的所有版本配置
        
        Args:
            strategy_type: 策略类型ID
        
        Returns:
            List[Dict]: 版本配置列表，每个包含 version, leverage, search_extend 等
        """
        # 使用缓存
        if strategy_type in self._strategy_versions_cache:
            return self._strategy_versions_cache[strategy_type]
        
        try:
            result = get_ai_strategy_list(self.token)
            if "error" in result:
                return []
            
            strategies = result.get("info", [])
            for s in strategies:
                if s.get("id") == strategy_type:
                    versions = s.get("versions", [])
                    self._strategy_versions_cache[strategy_type] = versions
                    return versions
            
            return []
        except Exception as e:
            self.log(f"⚠️  获取策略 {strategy_type} 的版本信息失败: {e}")
            return []
    
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
        查询并筛选策略
        
        Args:
            coins: 币种列表（可选，不传则使用默认主流币种）
            amt_type: 1现货 2合约
            sort_type: 1最新 2收益率 3夏普 4回撤
            strategy_type: 策略类型（可选，不传则查询多种类型）
            direction: long/short
            year: 年份
            ai_time_id: 时间ID
            recommand_type: 推荐类型 1=推荐 2=交易中策略
            limit: 每个币种查询数量
            min_sharpe: 最小夏普率
            max_drawdown: 最大回撤
        
        Returns:
            策略列表
        """
        # 1. 处理币种参数（从统一模块获取默认）
        if not coins:
            # 默认只使用虚拟币（CRYPTO），可通过配置修改
            coins = self.defaults.get_coins(coin_type=self.defaults.COIN_TYPE_FILTER)
            if self.defaults.COIN_TYPE_FILTER:
                self.log(f"ℹ️  未指定币种，使用默认币种（类型={self.defaults.COIN_TYPE_FILTER}）: {', '.join(coins)}")
            else:
                self.log(f"ℹ️  未指定币种，使用默认币种（全部{len(coins)}个）: {', '.join(coins[:5])}...")
        
        # 2. 处理策略类型参数（从统一模块获取默认）
        if strategy_type is None:
            strategy_types = self.defaults.get_strategy_types()
            self.log(f"ℹ️  未指定策略类型，查询多种类型（接口前{self.defaults.STRATEGY_COUNT}个）: {strategy_types}")
        else:
            strategy_types = [strategy_type]
        
        all_strategies = []
        
        # 3. 多维度查询
        for coin in coins:
            for st_type in strategy_types:
                # 获取该策略类型的所有版本配置
                versions = self.get_strategy_versions(st_type)
                
                if not versions:
                    # 如果没有版本信息，直接查询（不指定版本）
                    self.log(f"🔍 查询 {coin} / 策略类型 {st_type}...")
                    
                    result = query_backtest(
                        token=self.token,
                        search_coin=coin,
                        sort_type=sort_type,
                        strategy_type=st_type,
                        search_direction=direction,
                        search_year=year,
                        ai_time_id=ai_time_id,
                        search_recommand_type=recommand_type,
                        limit=limit
                    )
                    
                    if "error" not in result:
                        strategies = result.get("info", [])
                        self.log(f"✅ {coin} / 策略类型 {st_type} 找到 {len(strategies)} 个策略")
                        all_strategies.extend(strategies)
                    else:
                        self.log(f"⚠️  {coin} / 策略类型 {st_type} 查询失败: {result['error']}")
                else:
                    # 轮询该策略的所有版本配置
                    for ver_config in versions:
                        version = ver_config.get("version")
                        leverage = ver_config.get("leverage")
                        search_extend = ver_config.get("search_extend")
                        
                        self.log(f"🔍 查询 {coin} / 策略类型 {st_type} / 版本 {version} (杠杆{leverage})...")
                        
                        result = query_backtest(
                            token=self.token,
                            search_coin=coin,
                            sort_type=sort_type,
                            strategy_type=st_type,
                            search_direction=direction,
                            search_year=year,
                            ai_time_id=ai_time_id,
                            search_recommand_type=recommand_type,
                            version=str(version) if version else None,
                            leverage=leverage,
                            search_extend=search_extend,
                            limit=limit
                        )
                        
                        if "error" not in result:
                            strategies = result.get("info", [])
                            self.log(f"✅ {coin} / 策略 {st_type} / 版本 {version} 找到 {len(strategies)} 个策略")
                            all_strategies.extend(strategies)
                        else:
                            self.log(f"⚠️  {coin} / 策略 {st_type} / 版本 {version} 查询失败: {result['error']}")
        
        # 筛选
        if min_sharpe or max_drawdown:
            before = len(all_strategies)
            
            # 手动筛选（因为 API 返回的数据结构与 analysis 模块期望的不同）
            filtered = []
            for s in all_strategies:
                if min_sharpe and s.get("sharp_rate", 0) < min_sharpe:
                    continue
                if max_drawdown and s.get("max_loss", 100) > max_drawdown:
                    continue
                filtered.append(s)
            
            all_strategies = filtered
            self.log(f"🔽 筛选后剩余 {len(all_strategies)}/{before} 个策略")
        
        return all_strategies
    
    def enrich_with_details(self, strategies: List[Dict], max_fetch: int = 20) -> List[Dict]:
        """
        获取策略详情（净值曲线等）
        
        Args:
            strategies: 策略列表
            max_fetch: 最多获取详情数量（避免API调用过多）
        
        Returns:
            带详情的策略列表
        """
        self.log(f"📊 获取策略详情（最多 {min(len(strategies), max_fetch)} 个）...")
        
        enriched = []
        for i, strategy in enumerate(strategies[:max_fetch]):
            back_id = strategy.get("id")
            if not back_id:
                continue
            
            detail = get_backtest_detail(self.token, back_id)
            
            if "error" in detail:
                self.log(f"⚠️  策略 {back_id} 详情获取失败")
                continue
            
            # 合并基础信息和详情
            # detail 的结构: {strategy: [...], total_stat: {...}}
            # 我们需要提取 total_stat 作为根级别数据
            merged = {
                **strategy,  # 基础信息（id, name, strategy_token等）
                "total_stat": detail.get("total_stat", {}),
                "strategy": detail.get("strategy", []),  # 策略详情数组
            }
            enriched.append(merged)
            
            if self.verbose and (i + 1) % 5 == 0:
                self.log(f"   已获取 {i + 1}/{min(len(strategies), max_fetch)}")
        
        self.log(f"✅ 获取了 {len(enriched)} 个策略详情")
        return enriched
    
    def recommend(
        self,
        strategies: List[Dict],
        group_size: int = 3,
        top_n: int = 5,
        max_correlation: float = 0.5,
        max_drawdown: float = 20.0,
        min_sharpe: float = 1.5
    ) -> List[Dict]:
        """
        推荐组合
        
        Args:
            strategies: 策略列表（带详情）
            group_size: 组合大小
            top_n: 返回前N个
            max_correlation: 最大相关性
            max_drawdown: 最大回撤
            min_sharpe: 最小夏普
        
        Returns:
            推荐列表
        """
        if len(strategies) < group_size:
            self.log(f"⚠️  策略数量({len(strategies)})不足以组成{group_size}个策略的组合")
            return []
        
        self.log(f"🧠 分析 {len(strategies)} 个策略，寻找最优 {group_size} 策略组合...")
        
        preferences = {
            'max_correlation': max_correlation,
            'max_drawdown': max_drawdown,
            'min_sharpe': min_sharpe,
        }
        
        try:
            recommendations = recommend_combinations(
                strategies,
                group_size=group_size,
                top_n=top_n,
                preferences=preferences
            )
            
            self.log(f"✅ 找到 {len(recommendations)} 个推荐组合")
            return recommendations
            
        except Exception as e:
            self.log(f"❌ 组合分析失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def format_recommendation(self, rec: Dict, rank: int = 1) -> str:
        """格式化推荐结果"""
        lines = [f"\n{'='*60}"]
        lines.append(f"🏆 推荐组合 #{rank} (评分: {rec['score']:.1f}/100)")
        lines.append('='*60)
        
        # 策略列表
        lines.append("\n📋 策略列表:")
        for i, s in enumerate(rec['strategies'], 1):
            coin = s.get('coin', 'N/A')
            name = s.get('name', 'N/A')
            year_rate = s.get('year_rate', 0)
            sharp = s.get('sharp_rate', 0)
            drawdown = s.get('max_loss', 0)
            token = s.get('strategy_token', 'N/A')
            
            lines.append(f"   {i}. {name}")
            lines.append(f"      币种: {coin} | 年化: {year_rate}% | 夏普: {sharp:.2f} | 回撤: {drawdown}%")
            lines.append(f"      Token: {token}")
        
        # 组合分析
        lines.append("\n📊 组合分析:")
        lines.append(f"   相关性: {rec['correlation']:.3f} (越低越好，<0.5为佳)")
        lines.append(f"   组合夏普: {rec['portfolio_risk']['sharpe_ratio']:.2f}")
        lines.append(f"   组合回撤: {rec['portfolio_risk']['max_drawdown']:.2f}%")
        lines.append(f"   胜率: {rec['portfolio_risk']['win_rate']:.2f}%")
        lines.append(f"   回撤重叠: {rec['drawdown_overlap']:.1f}%")
        
        # 推荐理由
        lines.append(f"\n💡 推荐理由: {rec['reason']}")
        
        # 创建命令
        tokens = [s.get('strategy_token') for s in rec['strategies'] if s.get('strategy_token')]
        if tokens:
            cmd = f"python query.py --token <token> --create-group --group-name \"组合{rank}\" --strategy-tokens \"{','.join(tokens)}\""
            lines.append(f"\n🔧 创建命令:")
            lines.append(f"   {cmd}")
        
        lines.append('='*60)
        return '\n'.join(lines)
    
    def save_to_memory(self, recommendations: List[Dict], coins: Optional[List[str]], workspace: str):
        """保存到记忆文件"""
        memory_file = f"{workspace}/memory/portfolio_history.md"
        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            coins_str = '/'.join(coins) if coins else "多币种"
            content = f"\n## {timestamp} - {coins_str} 组合分析\n\n"
            content += f"**查询币种**: {', '.join(coins) if coins else '自动选择'}\n"
            content += f"**推荐数量**: {len(recommendations)}\n\n"
            
            for i, rec in enumerate(recommendations[:3], 1):  # 只记录前3个
                content += f"### 推荐 #{i} (评分: {rec['score']:.1f})\n\n"
                content += "**策略列表**:\n"
                for s in rec['strategies']:
                    content += f"- {s.get('name')} (年化{s.get('year_rate')}%, 夏普{s.get('sharp_rate'):.2f}, 回撤{s.get('max_loss')}%)\n"
                
                content += f"\n**组合指标**:\n"
                content += f"- 相关性: {rec['correlation']:.3f}\n"
                content += f"- 组合夏普: {rec['portfolio_risk']['sharpe_ratio']:.2f}\n"
                content += f"- 组合回撤: {rec['portfolio_risk']['max_drawdown']:.2f}%\n"
                content += f"- 回撤重叠: {rec['drawdown_overlap']:.1f}%\n"
                content += f"- 推荐理由: {rec['reason']}\n\n"
            
            content += "---\n"
            
            # 追加到文件
            with open(memory_file, 'a', encoding='utf-8') as f:
                f.write(content)
            
            self.log(f"💾 已保存到记忆: {memory_file}")
            
        except Exception as e:
            self.log(f"⚠️  保存记忆失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="智能策略组合推荐")
    
    # 基础参数
    parser.add_argument("--token", required=True, help="用户 token")
    parser.add_argument("--coins", help="币种列表（逗号分隔，可选，不传则使用默认主流币种）")
    parser.add_argument("--workspace", help="工作区路径（用于保存记忆）")
    
    # 查询参数
    parser.add_argument("--amt-type", type=int, default=2, choices=[1, 2], help="1现货 2合约")
    parser.add_argument("--sort", type=int, default=2, choices=[1, 2, 3, 4], help="1最新 2收益率 3夏普 4回撤")
    parser.add_argument("--strategy-type", type=int, help="策略类型（可选，不传则查询多种类型）")
    parser.add_argument("--direction", choices=["long", "short"], help="方向")
    parser.add_argument("--year", type=int, help="年份（注意：优先使用 --ai-time-id）")
    parser.add_argument("--ai-time-id", help="时间ID（推荐，默认5=最近1年，优先级高于 --year）")
    parser.add_argument("--recommand-type", type=int, default=1, choices=[1, 2], help="推荐类型: 1=推荐 2=交易中策略")
    parser.add_argument("--limit", type=int, default=10, help="每币种查询数量")
    
    # 筛选参数
    parser.add_argument("--min-sharpe", type=float, help="最小夏普率")
    parser.add_argument("--max-drawdown", type=float, help="最大回撤")
    
    # 组合参数
    parser.add_argument("--group-size", type=int, default=3, help="组合大小")
    parser.add_argument("--top-n", type=int, default=5, help="返回推荐数量")
    parser.add_argument("--max-correlation", type=float, default=0.5, help="最大相关性")
    parser.add_argument("--max-portfolio-drawdown", type=float, default=20.0, help="最大组合回撤")
    parser.add_argument("--min-portfolio-sharpe", type=float, default=1.5, help="最小组合夏普")
    
    # 输出参数
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    parser.add_argument("--no-detail", action="store_true", help="不获取详情（快速模式）")
    parser.add_argument("--save-memory", action="store_true", help="保存到记忆")
    
    args = parser.parse_args()
    
    # 处理币种参数
    coins = [c.strip() for c in args.coins.split(',')] if args.coins else None
    
    recommender = SmartRecommender(args.token, verbose=not args.quiet)
    
    # 验证参数 - 优先使用 ai_time_id，如果都没传则使用统一模块的默认值
    if not args.year and not args.ai_time_id:
        args.ai_time_id = recommender.defaults.get_ai_time_id()
        if not args.quiet:
            index_display = recommender.defaults.TIME_INDEX + 1
            print(f"ℹ️  未指定时间范围，使用默认（接口第{index_display}个）: ai_time_id={args.ai_time_id}")
    
    # 如果同时传了，优先用 ai_time_id
    if args.year and args.ai_time_id:
        if not args.quiet:
            print("⚠️  同时传入 --year 和 --ai-time-id，优先使用 --ai-time-id")
        args.year = None
    
    # 1. 查询策略
    strategies = recommender.fetch_strategies(
        coins=coins,  # 可以为 None
        amt_type=args.amt_type,
        sort_type=args.sort,
        strategy_type=args.strategy_type,
        direction=args.direction,
        year=args.year,
        ai_time_id=args.ai_time_id,
        recommand_type=args.recommand_type,
        limit=args.limit,
        min_sharpe=args.min_sharpe,
        max_drawdown=args.max_drawdown
    )
    
    if not strategies:
        print("❌ 未找到符合条件的策略")
        sys.exit(1)
    
    # 2. 获取详情（可选）
    if not args.no_detail:
        strategies = recommender.enrich_with_details(strategies)
        
        if not strategies:
            print("❌ 未能获取策略详情")
            sys.exit(1)
    
    # 3. 推荐组合
    recommendations = recommender.recommend(
        strategies=strategies,
        group_size=args.group_size,
        top_n=args.top_n,
        max_correlation=args.max_correlation,
        max_drawdown=args.max_portfolio_drawdown,
        min_sharpe=args.min_portfolio_sharpe
    )
    
    if not recommendations:
        print("❌ 未能生成推荐组合")
        sys.exit(1)
    
    # 4. 输出结果
    if args.format == "json":
        print(json.dumps(recommendations, indent=2, ensure_ascii=False))
    else:
        for i, rec in enumerate(recommendations, 1):
            print(recommender.format_recommendation(rec, i))
    
    # 5. 保存记忆（可选）
    if args.save_memory and args.workspace:
        recommender.save_to_memory(recommendations, coins, args.workspace)
    
    print(f"\n✅ 完成！共推荐 {len(recommendations)} 个组合")


if __name__ == "__main__":
    main()
