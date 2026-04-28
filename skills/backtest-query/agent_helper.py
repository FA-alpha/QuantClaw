#!/usr/bin/env python3
"""
Agent 辅助函数
用于简化推荐→创建的完整流程
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple


class StrategyRecommendHelper:
    """策略推荐辅助器"""
    
    def __init__(self, work_dir: str = "/home/ubuntu/work/QuantClaw"):
        self.work_dir = Path(work_dir)
        self.temp_dir = Path("/tmp")
    
    def detect_create_intent(self, query: str) -> bool:
        """
        检测用户是否有创建意图
        
        Args:
            query: 用户查询
        
        Returns:
            True 如果有创建意图
        """
        create_keywords = [
            "创建", "建立", "建个", "生成",
            "并创建", "然后创建", "帮我创建",
            "create", "make", "build", "generate"
        ]
        query_lower = query.lower()
        return any(kw in query_lower for kw in create_keywords)
    
    def recommend(
        self,
        query: str,
        coins: Optional[List[str]] = None,
        min_win_rate: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        top_per_group: int = 5,
        max_combinations: int = 10
    ) -> Tuple[bool, Dict]:
        """
        执行智能推荐
        
        Args:
            query: 用户需求描述
            coins: 币种列表
            min_win_rate: 最小胜率
            max_drawdown: 最大回撤
            top_per_group: 每组取几个
            max_combinations: 最多推荐几个组合
        
        Returns:
            (success, result_dict)
        """
        output_file = self.temp_dir / f"recommend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        cmd = [
            'python3',
            str(self.work_dir / 'skills/backtest-query/smart_group_recommend.py'),
            '--query', query,
            '--top-per-group', str(top_per_group),
            '--max-combinations', str(max_combinations),
            '--output', str(output_file)
        ]
        
        if coins:
            cmd.extend(['--coins', ','.join(coins)])
        if min_win_rate is not None:
            cmd.extend(['--min-total-win-rate', str(min_win_rate)])
        if max_drawdown is not None:
            cmd.extend(['--max-recent-drawdown', str(max_drawdown)])
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.work_dir),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return False, {"error": result.stderr}
            
            # 读取结果
            with open(output_file) as f:
                data = json.load(f)
            
            return True, data
            
        except Exception as e:
            return False, {"error": str(e)}
    
    def extract_tokens(self, combo: Dict) -> List[str]:
        """
        从推荐组合中提取 strategy_token
        
        Args:
            combo: 推荐组合数据
        
        Returns:
            token 列表
        """
        tokens = []
        for strategy in combo.get('strategies', []):
            token = strategy.get('strategy_token')
            if token:
                tokens.append(token)
        return tokens
    
    def create_group(
        self,
        tokens: List[str],
        group_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        创建策略组
        
        Args:
            tokens: strategy_token 列表
            group_name: 组合名称（可选，自动生成）
        
        Returns:
            (success, message)
        """
        if not tokens:
            return False, "没有有效的 strategy_token"
        
        if not group_name:
            group_name = f"智能组合_{datetime.now().strftime('%Y%m%d_%H%M')}"
        
        tokens_str = ','.join(tokens)
        
        cmd = [
            'python3',
            str(self.work_dir / 'skills/backtest-query/query.py'),
            '--create-group',
            '--group-name', group_name,
            '--strategy-tokens', tokens_str
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.work_dir),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return False, result.stderr
            
            return True, result.stdout
            
        except Exception as e:
            return False, str(e)
    
    def recommend_and_create(
        self,
        query: str,
        group_name: Optional[str] = None,
        **recommend_kwargs
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        一步完成：推荐 + 创建
        
        Args:
            query: 用户需求
            group_name: 组合名称（可选）
            **recommend_kwargs: 推荐参数
        
        Returns:
            (success, message, combo_data)
        """
        # 1. 执行推荐
        success, result = self.recommend(query, **recommend_kwargs)
        if not success:
            return False, f"推荐失败: {result.get('error')}", None
        
        # 2. 检查是否有推荐结果
        combinations = result.get('combinations', [])
        if not combinations:
            return False, "未找到符合条件的策略组合", None
        
        # 3. 获取最优组合
        best_combo = combinations[0]
        
        # 4. 提取 tokens
        tokens = self.extract_tokens(best_combo)
        if not tokens:
            return False, "推荐的策略缺少 strategy_token", best_combo
        
        # 5. 创建策略组
        success, message = self.create_group(tokens, group_name)
        if not success:
            return False, f"创建失败: {message}", best_combo
        
        return True, message, best_combo


# 使用示例
if __name__ == "__main__":
    helper = StrategyRecommendHelper()
    
    # 示例1：检测创建意图
    query1 = "帮我找 BTC 的优质策略并创建组合"
    query2 = "帮我找 BTC 的优质策略"
    
    print(f"'{query1}' 有创建意图: {helper.detect_create_intent(query1)}")
    print(f"'{query2}' 有创建意图: {helper.detect_create_intent(query2)}")
    
    # 示例2：完整流程
    print("\n" + "="*70)
    print("执行推荐...")
    success, result = helper.recommend(
        query="BTC优质策略",
        coins=["BTC"],
        max_drawdown=15
    )
    
    if success:
        print(f"✅ 推荐成功，找到 {len(result['combinations'])} 个组合")
        if result['combinations']:
            combo = result['combinations'][0]
            print(f"\n最优组合:")
            print(f"  评分: {combo['score']:.2f}")
            print(f"  预期收益: {combo['expected_return']:.2f}%")
            print(f"  回撤: {combo['portfolio_risk']['max_drawdown']:.2f}%")
            
            # 提取 tokens
            tokens = helper.extract_tokens(combo)
            print(f"  策略数量: {len(tokens)}")
            print(f"  Tokens: {tokens[:2]}..." if len(tokens) > 2 else f"  Tokens: {tokens}")
            
            # 可选：创建
            # success, msg = helper.create_group(tokens, "测试组合")
            # print(f"\n创建结果: {msg}")
    else:
        print(f"❌ 推荐失败: {result.get('error')}")
