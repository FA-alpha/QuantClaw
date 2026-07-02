"""
组合优化模块

评分双模式：
- has_net_value=True  → 净值曲线评分 (夏普+回撤+相关性+错位+二期指标)
- has_net_value=False → 列表字段评分 (年化+夏普+胜率+回撤+二期指标，无相关性/错位)
"""

import itertools
from typing import List, Dict, Optional, Tuple


def score_portfolio(
    strategies: List[Dict],
    selected_indices: List[int],
    weights: List[float] = None,
    preferences: Dict = None,
    has_net_value: bool = False,
) -> float:
    """
    为组合打分
    
    Args:
        strategies: 策略列表
        selected_indices: 选定的策略索引
        preferences: 用户偏好
        has_net_value: 是否有净值曲线数据
    
    Returns:
        float: 评分（越高越好）
    """
    if not selected_indices:
        return 0.0
    
    prefs = {
        'max_correlation': 0.5,
        'max_drawdown': 20.0,
        'min_sharpe': 1.5,
        'min_alpha': 0.0,
        'min_odds': 0.5,
        'max_recovery_days': 90,
        'max_dd_10pct_count': 10,
    }
    if preferences:
        prefs.update(preferences)
    
    selected_strategies = [strategies[i] for i in selected_indices]
    
    # 详情指标聚合
    detail_keys = ['alpha', 'beta', 'odds', 'max_recovery_time', 'drawdown_over_10pct_count']
    combo_detail = {}
    for k in detail_keys:
        vals = [s.get('_metrics', {}).get(k, 0) for s in selected_strategies]
        combo_detail[k] = sum(vals) / len(vals) if vals else 0
    
    def _avg(field, default=0):
        vals = [float(s.get(field, default) or 0) for s in selected_strategies]
        return sum(vals) / len(vals) if vals else 0
    
    score = 0.0

    # ================================================================
    # A. 净值曲线评分模式 (需要 risk_analyzer + correlation)
    # ================================================================
    if has_net_value:
        from .correlation import get_avg_correlation
        from .risk_analyzer import analyze_drawdown_overlap, calculate_portfolio_risk

        avg_corr = get_avg_correlation(strategies, selected_indices)
        risk = calculate_portfolio_risk(strategies, selected_indices, weights)
        overlap = analyze_drawdown_overlap(strategies, selected_indices)

        # 1. 夏普率 (0-35)
        sharpe = risk.get('sharpe_ratio', 0)
        score += min(sharpe / prefs['min_sharpe'] * 35, 35)

        # 2. 回撤 (0-25)
        drawdown = risk.get('max_drawdown', 100)
        if drawdown <= prefs['max_drawdown']:
            score += 25 * (1 - drawdown / prefs['max_drawdown'])

        # 3. 相关性 (0-15)
        if avg_corr <= prefs['max_correlation']:
            score += 15 * (1 - avg_corr / prefs['max_correlation'])

        # 4. 回撤错位 (0-5)
        overlap_ratio = overlap.get('overlap_ratio', 100)
        if overlap_ratio < 50:
            score += 5 * (1 - overlap_ratio / 50)

        # 5. Alpha (0-10)
        alpha = combo_detail['alpha']
        if alpha >= prefs['min_alpha']:
            score += min(alpha / max(prefs['min_alpha'], 0.01) * 5, 10)

        # 6. 赔率 (0-5)
        odds_val = combo_detail['odds']
        if odds_val >= prefs['min_odds']:
            score += min(odds_val / prefs['min_odds'] * 3, 5)

        # 7. 鲁棒性 (0-5)
        recovery_days = combo_detail['max_recovery_time']
        dd_10pct = combo_detail['drawdown_over_10pct_count']
        if recovery_days <= prefs['max_recovery_days']:
            score += 2.5 * (1 - recovery_days / prefs['max_recovery_days'])
        if dd_10pct <= prefs['max_dd_10pct_count']:
            score += 2.5 * (1 - dd_10pct / prefs['max_dd_10pct_count'])

        return round(score, 2)

    # ================================================================
    # B. 列表字段评分模式 (无净值曲线)
    # ================================================================

    # 1. 年化收益率 (0-25)
    avg_year_rate = _avg('year_rate')
    if avg_year_rate > 0:
        score += min(avg_year_rate / 100 * 25, 25)

    # 2. 夏普比率 (0-25)
    avg_sharpe = _avg('sharp_rate')
    if avg_sharpe >= prefs['min_sharpe']:
        score += min(avg_sharpe / prefs['min_sharpe'] * 15, 25)

    # 3. 胜率 (0-15)
    avg_win_rate = _avg('win_rate')
    if avg_win_rate > 0:
        score += min(avg_win_rate / 100 * 15, 15)

    # 4. 最大回撤 (0-15)
    avg_max_loss = _avg('max_loss', 100)
    if avg_max_loss <= prefs['max_drawdown']:
        score += 15 * (1 - avg_max_loss / prefs['max_drawdown'])

    # 5. Alpha (0-8)
    alpha = combo_detail['alpha']
    if alpha >= prefs['min_alpha']:
        score += min(alpha / max(prefs['min_alpha'], 0.01) * 4, 8)

    # 6. 赔率 (0-6)
    odds_val = combo_detail['odds']
    if odds_val >= prefs['min_odds']:
        score += min(odds_val / prefs['min_odds'] * 3, 6)

    # 7. 鲁棒性 (0-6)
    recovery_days = combo_detail['max_recovery_time']
    dd_10pct = combo_detail['drawdown_over_10pct_count']
    if recovery_days <= prefs['max_recovery_days']:
        score += 3 * (1 - recovery_days / prefs['max_recovery_days'])
    if dd_10pct <= prefs['max_dd_10pct_count']:
        score += 3 * (1 - dd_10pct / prefs['max_dd_10pct_count'])

    return round(score, 2)


# ================================================================
# 组合生成与优化
# ================================================================


def _has_net_value_data(strategies: List[Dict]) -> bool:
    """检测策略列表中是否有净值曲线数据"""
    for s in strategies[:1]:
        detail = s.get('_detail', {})
        nv = detail.get('total_stat', {}).get('net_value', {})
        if nv and nv.get('lists'):
            return True
    return False


def _generate_combinations_with_coin_coverage(
    strategies: List[Dict],
    group_size: int,
    required_coins: List[str],
    max_combinations: int
) -> List[Tuple[int, ...]]:
    """生成确保每个币种至少有一个策略的组合"""
    import random
    
    coin_strategies = {}
    for i, s in enumerate(strategies):
        coin = s.get('coin')
        if coin in required_coins:
            if coin not in coin_strategies:
                coin_strategies[coin] = []
            coin_strategies[coin].append(i)
    
    missing_coins = [c for c in required_coins if c not in coin_strategies or not coin_strategies[c]]
    available_coins = [c for c in required_coins if c in coin_strategies and coin_strategies[c]]
    
    if not available_coins:
        return []
    if len(available_coins) > group_size:
        # 币种太多无法全覆盖，流式随机采样代替全量 combinations
        import random
        all_combos = set()
        while len(all_combos) < max_combinations:
            combo = tuple(sorted(random.sample(range(len(strategies)), group_size)))
            all_combos.add(combo)
        return list(all_combos)
    
    valid_combinations = set()
    attempts = 0
    
    while len(valid_combinations) < max_combinations and attempts < max_combinations * 10:
        attempts += 1
        selected = [random.choice(coin_strategies[c]) for c in available_coins]
        remaining_slots = group_size - len(selected)
        if remaining_slots > 0:
            all_indices = [i for i in range(len(strategies)) if i not in selected]
            if len(all_indices) >= remaining_slots:
                selected.extend(random.sample(all_indices, remaining_slots))
        combo_tuple = tuple(sorted(selected))
        if len(combo_tuple) == group_size:
            valid_combinations.add(combo_tuple)
    
    return list(valid_combinations)


def optimize_portfolio(
    strategies: List[Dict],
    group_size: int = 3,
    max_combinations: int = 100000,
    preferences: Dict = None
) -> List[Dict]:
    """
    寻找最优组合。自动检测是否有净值曲线数据。
    无净值曲线 → 候选池上限 100000（纯字段评分便宜）
    有净值曲线 → 候选池上限 5000（相关性/风险分析较慢）
    """
    n = len(strategies)
    if n < group_size:
        raise ValueError(f"策略数量({n})少于组合大小({group_size})")
    
    has_net_value = _has_net_value_data(strategies)
    
    # 有净值曲线时评分开销大，自动限制候选池
    if has_net_value:
        max_combinations = min(max_combinations, 5000)
    
    required_coins = None
    if preferences and 'constraints' in preferences:
        required_coins = preferences['constraints'].get('coins')
    
    if required_coins and len(required_coins) > 1:
        all_combinations = _generate_combinations_with_coin_coverage(
            strategies, group_size, required_coins, max_combinations
        )
    else:
        # 流式随机采样，不物化全量组合避免 OOM
        import math
        import random
        total = math.comb(n, group_size)
        if total > max_combinations:
            all_combinations = set()
            while len(all_combinations) < max_combinations:
                combo = tuple(sorted(random.sample(range(n), group_size)))
                all_combinations.add(combo)
            all_combinations = list(all_combinations)
        else:
            all_combinations = list(itertools.combinations(range(n), group_size))
    
    from .risk_analyzer import calculate_portfolio_risk, analyze_drawdown_overlap
    
    results = []
    for combo in all_combinations:
        indices = list(combo)
        try:
            score = score_portfolio(strategies, indices, preferences=preferences, has_net_value=has_net_value)
            
            entry = {'indices': indices, 'score': score}
            entry['risk'] = calculate_portfolio_risk(strategies, indices)
            
            if has_net_value:
                from .correlation import get_avg_correlation
                entry['correlation'] = round(get_avg_correlation(strategies, indices), 3)
                entry['overlap'] = analyze_drawdown_overlap(strategies, indices)
            else:
                entry['correlation'] = 0
                entry['overlap'] = {'overlap_ratio': 100}
            
            results.append(entry)
        except Exception:
            continue
    
    results.sort(key=lambda x: x['score'], reverse=True)
    return results


def recommend_combinations(
    strategies: List[Dict],
    group_size: int = 3,
    top_n: int = 5,
    preferences: Dict = None
) -> List[Dict]:
    """推荐组合（简化接口）"""
    if not strategies:
        return []
    
    optimized = optimize_portfolio(strategies, group_size=group_size, preferences=preferences)
    
    recommendations = []
    for i, result in enumerate(optimized[:top_n], 1):
        indices = result['indices']
        selected = [strategies[idx] for idx in indices]
        risk = result.get('risk', {})
        overlap = result.get('overlap', {})
        
        recommendations.append({
            'rank': i,
            'score': result['score'],
            'expected_return': risk.get('expected_return', 0),
            'strategies': [
                {
                    'name': s.get('name'),
                    'coin': s.get('coin'),
                    'direction': s.get('direction'),
                    'year_rate': float(s.get('year_rate', 0)),
                    'sharp_rate': float(s.get('sharp_rate', 0)),
                    'max_loss': float(s.get('max_loss', 0)),
                    'strategy_token': s.get('strategy_token'),
                    '_detail': s.get('_detail', {}),
                }
                for s in selected
            ],
            'correlation': result.get('correlation', 0),
            'portfolio_risk': risk,
            'drawdown_overlap': overlap.get('overlap_ratio', 100),
            'reason': _generate_reason(result),
        })
    
    return recommendations


def _generate_reason(result: Dict) -> str:
    """生成推荐理由"""
    reasons = []
    
    corr = result.get('correlation', 0)
    if corr < 0.3:
        reasons.append(f"相关性极低({corr:.2f})")
    elif 0 < corr < 0.5:
        reasons.append(f"相关性较低({corr:.2f})")
    
    risk = result.get('risk', {})
    sharpe = risk.get('sharpe_ratio', 0)
    if sharpe > 2.0:
        reasons.append(f"高夏普率({sharpe:.2f})")
    drawdown = risk.get('max_drawdown', 0)
    if 0 < drawdown < 15:
        reasons.append(f"低回撤({drawdown:.1f}%)")
    
    overlap = result.get('overlap', {})
    overlap_ratio = overlap.get('overlap_ratio', 100)
    if overlap_ratio < 30:
        reasons.append(f"回撤错位良好({overlap_ratio:.1f}%重叠)")
    
    return "、".join(reasons) if reasons else "综合评分较高"


def filter_by_criteria(
    strategies: List[Dict],
    min_sharpe: float = None,
    max_drawdown: float = None,
    min_year_rate: float = None,
    coins: List[str] = None,
    directions: List[str] = None
) -> List[Dict]:
    """按条件筛选策略"""
    filtered = strategies
    
    if min_sharpe is not None:
        filtered = [s for s in filtered if float(s.get('sharp_rate', 0) or 0) >= min_sharpe]
    if max_drawdown is not None:
        filtered = [s for s in filtered if float(s.get('max_loss', 100) or 100) <= max_drawdown]
    if min_year_rate is not None:
        filtered = [s for s in filtered if float(s.get('year_rate', 0) or 0) >= min_year_rate]
    if coins:
        filtered = [s for s in filtered if s.get('coin') in coins]
    if directions:
        filtered = [s for s in filtered if s.get('direction') in directions]
    
    return filtered