#!/usr/bin/env python3
"""简单测试"""

from analysis.correlation import calculate_correlation

# 测试相关性计算
net_a = [10000, 10100, 10200, 10150, 10300]
net_b = [10000, 10050, 10100, 10200, 10250]

corr = calculate_correlation(net_a, net_b)
print(f"✅ 相关性计算成功: {corr:.3f}")

# 测试风险分析
from analysis.risk_analyzer import find_drawdown_periods

net_values = [
    {'date': '2024-01-01', 'net': 10000},
    {'date': '2024-01-02', 'net': 10100},
    {'date': '2024-01-03', 'net': 9900},  # 回撤开始
    {'date': '2024-01-04', 'net': 9850},  # 最低点
    {'date': '2024-01-05', 'net': 10200},  # 恢复
]

periods = find_drawdown_periods(net_values)
print(f"✅ 回撤期识别成功: 找到 {len(periods)} 个回撤期")
for start, end, depth in periods:
    print(f"   {start} ~ {end}: -{depth:.2f}%")

print("\n🎉 基础分析模块工作正常！")
