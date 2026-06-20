"""
组合优化模块
"""

import itertools
from typing import List, Dict, Optional, Tuple
from .correlation import build_correlation_matrix, get_avg_correlation
from .risk_analyzer import analyze_drawdown_overlap, calculate_portfolio_risk


def score_portfolio(
    strategies: List[Dict],
    selected_indices: List[int],
    weights: List[float] = None,
    preferences: Dict = None
) -> float:
    """
    为组合打分
    
    Args:
        strategies: 策略列表
        selected_indices: 选定的策略索引
        weights: 权重
        preferences: 用户偏好 {
            'max_correlation': 最大相关性,
            'max_drawdown': 最大回撤,
            'min_sharpe': 最小夏普,
            'risk_weight': 风险权重 (0-1)
        }
    
    Returns:
        float: 评分（越高越好）
    """
    if not selected_indices:
        return 0.0
    
    # 默认偏好
    prefs = {
        'max_correlation': 0.5,
        'max_drawdown': 20.0,
        'min_sharpe': 1.5,
        'risk_weight': 0.4,  # 40%权重给风险，60%给收益
        # 二期权重偏好
        'min_alpha': 0.0,
        'min_odds': 0.5,
        'max_recovery_days': 90,
        'max_dd_10pct_count': 10,
    }
    if preferences:
        prefs.update(preferences)
    
    # 计算组合指标
    avg_corr = get_avg_correlation(strategies, selected_indices)
    risk = calculate_portfolio_risk(strategies, selected_indices, weights)
    overlap = analyze_drawdown_overlap(strategies, selected_indices)
    
    # 组合级别的详情指标聚合
    selected_strategies = [strategies[i] for i in selected_indices]
    detail_keys = ['alpha', 'beta', 'odds', 'max_recovery_time', 'drawdown_over_10pct_count']
    combo_detail = {}
    for k in detail_keys:
        vals = [s.get('_metrics', {}).get(k, 0) for s in selected_strategies]
        combo_detail[k] = sum(vals) / len(vals) if vals else 0
    
    # 评分组件
    score = 0.0
    
    # 1. 夏普率得分（0-35分）
    sharpe = risk.get('sharpe_ratio', 0)
    sharpe_score = min(sharpe / prefs['min_sharpe'] * 35, 35)
    score += sharpe_score
    
    # 2. 回撤得分（0-25分）
    drawdown = risk.get('max_drawdown', 100)
    if drawdown <= prefs['max_drawdown']:
        drawdown_score = 25 * (1 - drawdown / prefs['max_drawdown'])
    else:
        drawdown_score = 0
    score += drawdown_score
    
    # 3. 相关性得分（0-15分）
    if avg_corr <= prefs['max_correlation']:
        corr_score = 15 * (1 - avg_corr / prefs['max_correlation'])
    else:
        corr_score = 0
    score += corr_score
    
    # 4. 回撤错位得分（0-5分）
    overlap_ratio = overlap.get('overlap_ratio', 100)
    if overlap_ratio < 50:
        overlap_score = 5 * (1 - overlap_ratio / 50)
    else:
        overlap_score = 0
    score += overlap_score
    
    # === 二期权重：详情指标 ===
    
    # 5. Alpha 超额收益（0-10分）
    alpha = combo_detail['alpha']
    if alpha >= prefs['min_alpha']:
        alpha_score = min(alpha / max(prefs['min_alpha'], 0.01) * 5, 10)
    else:
        alpha_score = 0
    score += alpha_score
    
    # 6. 赔率 Odds（0-5分）
    odds_val = combo_detail['odds']
    if odds_val >= prefs['min_odds']:
        odds_score = min(odds_val / prefs['min_odds'] * 3, 5)
    else:
        odds_score = 0
    score += odds_score
    
    # 7. 鲁棒性：修复时间 + 大回撤次数（0-5分）
    recovery_days = combo_detail['max_recovery_time']
    dd_10pct = combo_detail['drawdown_over_10pct_count']
    recovery_score = 0
    if recovery_days <= prefs['max_recovery_days']:
        recovery_score += 2.5 * (1 - recovery_days / prefs['max_recovery_days'])
    if dd_10pct <= prefs['max_dd_10pct_count']:
        recovery_score += 2.5 * (1 - dd_10pct / prefs['max_dd_10pct_count'])
    score += recovery_score
    score += overlap_score
    
    return round(score, 2)


def _generate_combinations_with_coin_coverage(
    strategies: List[Dict],
    group_size: int,
    required_coins: List[str],
    max_combinations: int
) -> List[Tuple[int, ...]]:
    """
    生成确保每个币种至少有一个策略的组合
    
    Args:
        strategies: 策略列表
        group_size: 组合大小
        required_coins: 必须覆盖的币种列表
        max_combinations: 最大组合数
    
    Returns:
        list: 符合条件的组合列表（索引元组）
    """
    import random
    
    # 按币种分组策略
    coin_strategies = {}
    for i, s in enumerate(strategies):
        coin = s.get('coin')
        if coin in required_coins:
            if coin not in coin_strategies:
                coin_strategies[coin] = []
            coin_strategies[coin].append(i)
    
    # 检查是否所有币种都有策略
    missing_coins = [c for c in required_coins if c not in coin_strategies or not coin_strategies[c]]
    if missing_coins:
        # 如果有币种没有策略，放宽限制（警告但不强制）
        print(f"⚠️  部分币种无可用策略: {', '.join(missing_coins)}，组合中可能不包含这些币种")
        available_coins = [c for c in required_coins if c in coin_strategies and coin_strategies[c]]
    else:
        available_coins = required_coins
    
    # 如果没有足够的币种或组合大小小于币种数，无法满足要求
    if len(available_coins) > group_size:
        print(f"⚠️  组合大小({group_size})小于币种数量({len(available_coins)})，无法确保每个币种都有策略")
        # 降级为普通组合生成
        return list(itertools.combinations(range(len(strategies)), group_size))[:max_combinations]
    
    # 生成组合：从每个币种至少选一个，剩余位置随机分配
    valid_combinations = set()
    attempts = 0
    max_attempts = max_combinations * 10  # 最多尝试10倍
    
    while len(valid_combinations) < max_combinations and attempts < max_attempts:
        attempts += 1
        
        # 1. 从每个币种至少选一个策略
        selected = []
        for coin in available_coins:
            selected.append(random.choice(coin_strategies[coin]))
        
        # 2. 剩余位置从所有策略中随机选择（不重复）
        remaining_slots = group_size - len(selected)
        if remaining_slots > 0:
            all_indices = [i for i in range(len(strategies)) if i not in selected]
            if len(all_indices) >= remaining_slots:
                selected.extend(random.sample(all_indices, remaining_slots))
        
        # 转为元组并去重
        combo_tuple = tuple(sorted(selected))
        if len(combo_tuple) == group_size:  # 确保组合大小正确
            valid_combinations.add(combo_tuple)
    
    return list(valid_combinations)


def optimize_portfolio(
    strategies: List[Dict],
    group_size: int = 3,
    max_combinations: int = 1000,
    preferences: Dict = None
) -> List[Dict]:
    """
    寻找最优组合
    
    Args:
        strategies: 策略列表
        group_size: 组合大小
        max_combinations: 最大尝试组合数
        preferences: 用户偏好（可包含 constraints.coins 要求每个币种至少1个策略）
    
    Returns:
        list: 推荐组合列表，每个包含 {
            'indices': 策略索引,
            'score': 评分,
            'correlation': 平均相关性,
            'risk': 风险指标,
            'overlap': 回撤重叠
        }
    """
    n = len(strategies)
    if n < group_size:
        raise ValueError(f"策略数量({n})少于组合大小({group_size})")
    
    # 检查是否需要确保每个币种都有策略
    required_coins = None
    if preferences and 'constraints' in preferences:
        required_coins = preferences['constraints'].get('coins')
    
    # 生成所有可能的组合
    if required_coins and len(required_coins) > 1:
        # 确保每个币种至少有一个策略
        all_combinations = _generate_combinations_with_coin_coverage(
            strategies, group_size, required_coins, max_combinations
        )
    else:
        # 默认：生成所有可能的组合
        all_combinations = list(itertools.combinations(range(n), group_size))
        
        # 限制计算量
        if len(all_combinations) > max_combinations:
            # 随机采样
            import random
            all_combinations = random.sample(all_combinations, max_combinations)
    
    # 评估每个组合
    results = []
    for combo in all_combinations:
        indices = list(combo)
        
        try:
            score = score_portfolio(strategies, indices, preferences=preferences)
            avg_corr = get_avg_correlation(strategies, indices)
            risk = calculate_portfolio_risk(strategies, indices)
            overlap = analyze_drawdown_overlap(strategies, indices)
            
            results.append({
                'indices': indices,
                'score': score,
                'correlation': round(avg_corr, 3),
                'risk': risk,
                'overlap': overlap
            })
        except Exception as e:
            # 跳过有问题的组合
            continue
    
    # 按评分排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results


def recommend_combinations(
    strategies: List[Dict],
    group_size: int = 3,
    top_n: int = 5,
    preferences: Dict = None
) -> List[Dict]:
    """
    推荐组合（简化接口）
    
    Args:
        strategies: 策略列表
        group_size: 组合大小
        top_n: 返回前N个推荐
        preferences: 用户偏好
    
    Returns:
        list: 推荐组合，带详细说明
    """
    if not strategies:
        return []
    
    # 优化组合
    optimized = optimize_portfolio(
        strategies,
        group_size=group_size,
        preferences=preferences
    )
    
    # 取前N个
    recommendations = []
    for i, result in enumerate(optimized[:top_n], 1):
        indices = result['indices']
        selected = [strategies[idx] for idx in indices]
        
        recommendations.append({
            'rank': i,
            'score': result['score'],
            'expected_return': result['risk'].get('expected_return', 0),  # 从 risk 中提取
            'strategies': [
                {
                    'name': s.get('name'),
                    'coin': s.get('coin') or (s.get('strategy', [{}])[0].get('coin') if isinstance(s.get('strategy'), list) else None),
                    'direction': s.get('direction'),  # 保留 direction 字段
                    'year_rate': float(s.get('year_rate', 0)),
                    'sharp_rate': float(s.get('sharp_rate', 0)),
                    'max_loss': float(s.get('max_loss', 0)),
                    'strategy_token': s.get('strategy_token')
                }
                for s in selected
            ],
            'correlation': result['correlation'],
            'portfolio_risk': result['risk'],
            'drawdown_overlap': result['overlap']['overlap_ratio'],
            'reason': _generate_reason(result)
        })
    
    return recommendations


def _generate_reason(result: Dict) -> str:
    """生成推荐理由"""
    reasons = []
    
    # 相关性
    corr = result['correlation']
    if corr < 0.3:
        reasons.append(f"相关性极低({corr:.2f})")
    elif corr < 0.5:
        reasons.append(f"相关性较低({corr:.2f})")
    
    # 夏普率
    sharpe = result['risk'].get('sharpe_ratio', 0)
    if sharpe > 2.0:
        reasons.append(f"高夏普率({sharpe:.2f})")
    
    # 回撤
    drawdown = result['risk'].get('max_drawdown', 0)
    if drawdown < 15:
        reasons.append(f"低回撤({drawdown:.1f}%)")
    
    # 回撤错位
    overlap = result['overlap']['overlap_ratio']
    if overlap < 30:
        reasons.append(f"回撤错位良好({overlap:.1f}%重叠)")
    
    return "、".join(reasons) if reasons else "综合评分较高"


def filter_by_criteria(
    strategies: List[Dict],
    min_sharpe: float = None,
    max_drawdown: float = None,
    min_year_rate: float = None,
    coins: List[str] = None,
    directions: List[str] = None
) -> List[Dict]:
    """
    按条件筛选策略
    
    Args:
        strategies: 策略列表
        min_sharpe: 最小夏普率
        max_drawdown: 最大回撤
        min_year_rate: 最小年化收益
        coins: 币种列表
        directions: 方向列表 (long/short)
    
    Returns:
        list: 筛选后的策略
    """
    filtered = strategies
    
    if min_sharpe is not None:
        filtered = [
            s for s in filtered
            if s.get('total_stat', {}).get('sharp_rate', 0) >= min_sharpe
        ]
    
    if max_drawdown is not None:
        filtered = [
            s for s in filtered
            if s.get('total_stat', {}).get('max_loss', 100) <= max_drawdown
        ]
    
    if min_year_rate is not None:
        filtered = [
            s for s in filtered
            if s.get('total_stat', {}).get('year_rate', 0) >= min_year_rate
        ]
    
    if coins:
        filtered = [
            s for s in filtered
            if any(
                strat.get('coin') in coins
                for strat in (s.get('strategy', []) if isinstance(s.get('strategy'), list) else [])
            )
        ]
    
    if directions:
        filtered = [
            s for s in filtered
            if any(
                strat.get('direction') in directions
                for strat in (s.get('strategy', []) if isinstance(s.get('strategy'), list) else [])
            )
        ]
    
    return filtered
