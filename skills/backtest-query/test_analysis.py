#!/usr/bin/env python3
"""
测试分析模块
"""

import sys
import json
from analysis import recommend_combinations, filter_by_criteria


def test_with_mock_data():
    """使用模拟数据测试"""
    
    # 模拟策略数据
    mock_strategies = [
        {
            'id': 1,
            'name': 'BTC风霆做多',
            'strategy_token': 'st_btc_001',
            'strategy': [{'coin': 'BTC', 'direction': 'long'}],
            'total_stat': {
                'year_rate': 35.5,
                'sharp_rate': 2.1,
                'max_loss': 12.3,
                'win_rate': 65.0,
                'net_value': {
                    'lists': [
                        {'date': '2024-01-01', 'net': 10000},
                        {'date': '2024-01-02', 'net': 10100},
                        {'date': '2024-01-03', 'net': 10200},
                        {'date': '2024-01-04', 'net': 10150},
                        {'date': '2024-01-05', 'net': 10300},
                    ]
                }
            }
        },
        {
            'id': 2,
            'name': 'ETH鲲鹏震荡',
            'strategy_token': 'st_eth_002',
            'strategy': [{'coin': 'ETH', 'direction': 'long'}],
            'total_stat': {
                'year_rate': 28.3,
                'sharp_rate': 1.9,
                'max_loss': 9.5,
                'win_rate': 68.0,
                'net_value': {
                    'lists': [
                        {'date': '2024-01-01', 'net': 10000},
                        {'date': '2024-01-02', 'net': 10050},
                        {'date': '2024-01-03', 'net': 10100},
                        {'date': '2024-01-04', 'net': 10200},
                        {'date': '2024-01-05', 'net': 10250},
                    ]
                }
            }
        },
        {
            'id': 3,
            'name': 'SOL网格策略',
            'strategy_token': 'st_sol_003',
            'strategy': [{'coin': 'SOL', 'direction': 'long'}],
            'total_stat': {
                'year_rate': 42.1,
                'sharp_rate': 1.7,
                'max_loss': 18.7,
                'win_rate': 62.0,
                'net_value': {
                    'lists': [
                        {'date': '2024-01-01', 'net': 10000},
                        {'date': '2024-01-02', 'net': 10150},
                        {'date': '2024-01-03', 'net': 9950},
                        {'date': '2024-01-04', 'net': 10100},
                        {'date': '2024-01-05', 'net': 10300},
                    ]
                }
            }
        },
    ]
    
    print("=" * 60)
    print("测试组合优化模块")
    print("=" * 60)
    
    # 测试筛选
    print("\n1. 测试策略筛选（夏普>1.8，回撤<15%）")
    filtered = filter_by_criteria(
        mock_strategies,
        min_sharpe=1.8,
        max_drawdown=15.0
    )
    print(f"   筛选后剩余 {len(filtered)} 个策略:")
    for s in filtered:
        print(f"   - {s['name']}: 夏普{s['total_stat']['sharp_rate']}, 回撤{s['total_stat']['max_loss']}%")
    
    # 测试组合推荐
    print("\n2. 测试组合推荐（2策略组合，Top 3）")
    recommendations = recommend_combinations(
        mock_strategies,
        group_size=2,
        top_n=3,
        preferences={
            'max_correlation': 0.5,
            'max_drawdown': 20.0,
            'min_sharpe': 1.5
        }
    )
    
    for rec in recommendations:
        print(f"\n   🏆 推荐 #{rec['rank']} (评分: {rec['score']:.1f})")
        print(f"      策略组合:")
        for s in rec['strategies']:
            print(f"        - {s['name']} (年化{s['year_rate']}%, 夏普{s['sharp_rate']}, 回撤{s['max_loss']}%)")
        print(f"      相关性: {rec['correlation']:.3f}")
        print(f"      组合夏普: {rec['portfolio_risk']['sharpe_ratio']:.2f}")
        print(f"      组合回撤: {rec['portfolio_risk']['max_drawdown']:.2f}%")
        print(f"      回撤重叠: {rec['drawdown_overlap']:.1f}%")
        print(f"      推荐理由: {rec['reason']}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


def test_with_real_data(strategies_json: str):
    """使用真实数据测试"""
    
    with open(strategies_json, 'r') as f:
        strategies = json.load(f)
    
    print(f"加载了 {len(strategies)} 个策略")
    
    # 推荐组合
    recommendations = recommend_combinations(
        strategies,
        group_size=3,
        top_n=5
    )
    
    for rec in recommendations:
        print(f"\n推荐 #{rec['rank']} (评分: {rec['score']:.1f})")
        for s in rec['strategies']:
            print(f"  - {s['name']}")
        print(f"  相关性: {rec['correlation']:.3f}")
        print(f"  组合夏普: {rec['portfolio_risk']['sharpe_ratio']:.2f}")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 使用真实数据
        test_with_real_data(sys.argv[1])
    else:
        # 使用模拟数据
        test_with_mock_data()
