"""
风险分析模块
"""

import numpy as np
from typing import List, Dict, Tuple
from datetime import datetime, timedelta


def find_drawdown_periods(net_value_lists: List[Dict]) -> List[Tuple[str, str, float]]:
    """
    识别回撤期
    
    Args:
        net_value_lists: 净值列表 [{"date": "2024-01-01", "net": 10500}, ...]
    
    Returns:
        list: [(开始日期, 结束日期, 回撤幅度), ...]
    """
    if not net_value_lists:
        return []
    
    drawdown_periods = []
    peak_value = net_value_lists[0]['net']
    peak_date = net_value_lists[0]['date']
    in_drawdown = False
    dd_start = None
    
    for i, item in enumerate(net_value_lists):
        current_value = item['net']
        current_date = item['date']
        
        # 更新峰值
        if current_value >= peak_value:
            # 如果正在回撤中，记录回撤结束
            if in_drawdown and dd_start:
                dd_depth = (peak_value - min_value) / peak_value * 100
                if dd_depth > 0.01:  # 回撤>0.01%才记录
                    drawdown_periods.append((dd_start, net_value_lists[i-1]['date'], dd_depth))
                in_drawdown = False
            
            peak_value = current_value
            peak_date = current_date
        else:
            # 进入回撤
            if not in_drawdown:
                in_drawdown = True
                dd_start = current_date
                min_value = current_value
            else:
                min_value = min(min_value, current_value)
    
    # 处理未结束的回撤
    if in_drawdown and dd_start:
        dd_depth = (peak_value - min_value) / peak_value * 100
        if dd_depth > 0.01:
            drawdown_periods.append((dd_start, net_value_lists[-1]['date'], dd_depth))
    
    return drawdown_periods


def analyze_drawdown_overlap(
    strategies: List[Dict],
    selected_indices: List[int]
) -> Dict:
    """
    分析选定策略的回撤重叠情况
    
    Args:
        strategies: 所有策略列表
        selected_indices: 选定的策略索引
    
    Returns:
        dict: {
            'overlap_ratio': 回撤重叠比例,
            'max_concurrent_drawdowns': 最大同时回撤数量,
            'periods': 各策略回撤期详情
        }
    """
    if len(selected_indices) < 2:
        return {'overlap_ratio': 0.0, 'max_concurrent_drawdowns': 0, 'periods': []}
    
    # 收集各策略的回撤期
    all_periods = []
    for idx in selected_indices:
        strategy = strategies[idx]
        # 尝试从 _detail 或顶层获取 net_value
        detail = strategy.get('_detail', {})
        total_stat = detail.get('total_stat', {}) if detail else strategy.get('total_stat', {})
        net_value = total_stat.get('net_value', {}).get('lists', [])
        if not net_value:
            continue
        
        periods = find_drawdown_periods(net_value)
        all_periods.append({
            'strategy_id': idx,
            'strategy_name': strategy.get('name', f'Strategy {idx}'),
            'periods': periods
        })
    
    # 计算重叠
    if not all_periods:
        return {'overlap_ratio': 0.0, 'max_concurrent_drawdowns': 0, 'periods': []}
    
    # 构建时间轴上的回撤事件
    events = []
    for item in all_periods:
        for start, end, depth in item['periods']:
            events.append({
                'start': datetime.strptime(start, '%Y-%m-%d'),
                'end': datetime.strptime(end, '%Y-%m-%d'),
                'strategy_id': item['strategy_id'],
                'depth': depth
            })
    
    if not events:
        return {'overlap_ratio': 0.0, 'max_concurrent_drawdowns': 0, 'periods': all_periods}
    
    # 计算重叠天数
    all_dates = set()
    for event in events:
        date = event['start']
        while date <= event['end']:
            all_dates.add(date)
            date += timedelta(days=1)
    
    overlap_days = 0
    max_concurrent = 0
    
    for date in all_dates:
        concurrent = sum(1 for e in events if e['start'] <= date <= e['end'])
        if concurrent > 1:
            overlap_days += 1
        max_concurrent = max(max_concurrent, concurrent)
    
    total_days = len(all_dates) if all_dates else 1
    overlap_ratio = (overlap_days / total_days * 100) if total_days > 0 else 0.0
    
    return {
        'overlap_ratio': round(overlap_ratio, 2),
        'max_concurrent_drawdowns': max_concurrent,
        'periods': all_periods
    }


def calculate_portfolio_risk(
    strategies: List[Dict],
    selected_indices: List[int],
    weights: List[float] = None
) -> Dict:
    """
    计算组合风险指标
    
    Args:
        strategies: 策略列表
        selected_indices: 选定的策略索引
        weights: 权重（默认等权）
    
    Returns:
        dict: {
            'max_drawdown': 组合最大回撤,
            'sharpe_ratio': 组合夏普率,
            'volatility': 波动率,
            'win_rate': 平均胜率
        }
    """
    if not selected_indices:
        return {}
    
    n = len(selected_indices)
    if weights is None:
        weights = [1.0 / n] * n
    
    # 提取各策略统计
    selected = [strategies[i] for i in selected_indices]
    
    # 加权平均
    max_drawdown = sum(
        float(s.get('max_loss', 0)) * w
        for s, w in zip(selected, weights)
    )
    
    sharpe_ratio = sum(
        float(s.get('sharp_rate', 0)) * w
        for s, w in zip(selected, weights)
    )
    
    # win_rate 可能在 _metrics 或顶层
    win_rate = sum(
        float(s.get('_metrics', {}).get('total_win_rate', 0) or s.get('win_rate', 0)) * w
        for s, w in zip(selected, weights)
    )
    
    # 计算波动率（基于净值序列）
    all_returns = []
    for s in selected:
        # 尝试从 _detail 或顶层获取 net_value
        detail = s.get('_detail', {})
        total_stat = detail.get('total_stat', {}) if detail else s.get('total_stat', {})
        net_values = [item['net'] for item in total_stat.get('net_value', {}).get('lists', [])]
        if len(net_values) > 1:
            returns = np.diff(net_values) / net_values[:-1]
            all_returns.extend(returns)
    
    volatility = float(np.std(all_returns) * 100) if all_returns else 0.0
    
    return {
        'max_drawdown': round(max_drawdown, 2),
        'sharpe_ratio': round(sharpe_ratio, 2),
        'volatility': round(volatility, 2),
        'win_rate': round(win_rate, 2)
    }
