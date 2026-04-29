"""
相关性分析模块
"""

import numpy as np
from typing import List, Dict, Tuple


def calculate_correlation(net_values_a: List[float], net_values_b: List[float]) -> float:
    """
    计算两个策略的净值相关性
    
    Args:
        net_values_a: 策略A的净值序列
        net_values_b: 策略B的净值序列
    
    Returns:
        float: 相关系数 [-1, 1]
    """
    if len(net_values_a) != len(net_values_b):
        raise ValueError("净值序列长度必须相同")
    
    if len(net_values_a) < 2:
        return 0.0
    
    # 计算收益率序列
    returns_a = np.diff(net_values_a) / net_values_a[:-1]
    returns_b = np.diff(net_values_b) / net_values_b[:-1]
    
    # 计算皮尔逊相关系数
    correlation = np.corrcoef(returns_a, returns_b)[0, 1]
    
    # 处理 NaN（如果数据无变化）
    if np.isnan(correlation):
        return 0.0
    
    return float(correlation)


def build_correlation_matrix(strategies: List[Dict]) -> Tuple[np.ndarray, List[str]]:
    """
    构建策略相关性矩阵
    
    Args:
        strategies: 策略列表，每个策略包含 net_value.lists
    
    Returns:
        tuple: (相关性矩阵, 策略名称列表)
    """
    n = len(strategies)
    matrix = np.eye(n)  # 对角线为1
    names = []
    
    for i, strategy in enumerate(strategies):
        names.append(strategy.get('name', f"Strategy {i+1}"))
    
    # 计算两两相关性
    for i in range(n):
        # 尝试从 _detail 或顶层获取 net_value
        detail_i = strategies[i].get('_detail', {})
        total_stat_i = detail_i.get('total_stat', {}) if detail_i else strategies[i].get('total_stat', {})
        net_value_i = total_stat_i.get('net_value', {}).get('lists', [])
        
        if not net_value_i:
            continue
        
        net_a = [item['net'] for item in net_value_i]
        
        for j in range(i + 1, n):
            detail_j = strategies[j].get('_detail', {})
            total_stat_j = detail_j.get('total_stat', {}) if detail_j else strategies[j].get('total_stat', {})
            net_value_j = total_stat_j.get('net_value', {}).get('lists', [])
            
            if not net_value_j:
                continue
            
            net_b = [item['net'] for item in net_value_j]
            
            # 对齐日期（取交集）
            dates_a = {item['date']: item['net'] for item in net_value_i}
            dates_b = {item['date']: item['net'] for item in net_value_j}
            common_dates = sorted(set(dates_a.keys()) & set(dates_b.keys()))
            
            if len(common_dates) < 2:
                matrix[i, j] = matrix[j, i] = 0.0
                continue
            
            aligned_a = [dates_a[date] for date in common_dates]
            aligned_b = [dates_b[date] for date in common_dates]
            
            corr = calculate_correlation(aligned_a, aligned_b)
            matrix[i, j] = matrix[j, i] = corr
    
    return matrix, names


def get_avg_correlation(strategies: List[Dict], selected_indices: List[int]) -> float:
    """
    计算选定策略的平均相关性
    
    Args:
        strategies: 所有策略列表
        selected_indices: 选定的策略索引
    
    Returns:
        float: 平均相关系数
    """
    if len(selected_indices) < 2:
        return 0.0
    
    selected = [strategies[i] for i in selected_indices]
    matrix, _ = build_correlation_matrix(selected)
    
    # 只取上三角（不含对角线）
    upper_triangle = matrix[np.triu_indices_from(matrix, k=1)]
    
    return float(np.mean(upper_triangle))


def find_low_correlation_pairs(
    strategies: List[Dict],
    max_correlation: float = 0.5
) -> List[Tuple[int, int, float]]:
    """
    找出低相关性的策略对
    
    Args:
        strategies: 策略列表
        max_correlation: 最大相关性阈值
    
    Returns:
        list: [(索引A, 索引B, 相关系数), ...]，按相关性从低到高排序
    """
    matrix, _ = build_correlation_matrix(strategies)
    pairs = []
    
    n = len(strategies)
    for i in range(n):
        for j in range(i + 1, n):
            corr = matrix[i, j]
            if abs(corr) <= max_correlation:
                pairs.append((i, j, corr))
    
    # 按相关性绝对值排序（越低越好）
    pairs.sort(key=lambda x: abs(x[2]))
    
    return pairs
