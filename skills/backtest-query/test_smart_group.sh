#!/bin/bash
# 智能分组推荐系统测试脚本

echo "========================================"
echo "🧪 智能分组推荐系统测试"
echo "========================================"

cd "$(dirname "$0")"

echo ""
echo "测试1: 按币种分组推荐"
echo "----------------------------------------"
python3 smart_group_recommend.py \
  --query "帮我找BTC的最优策略" \
  --coins "BTC" \
  --top-per-group 3 \
  --min-total-win-rate 50 \
  --max-combinations 3

echo ""
echo ""
echo "测试2: 多币种分组（如果需要更多测试可以取消注释）"
echo "----------------------------------------"
# python3 smart_group_recommend.py \
#   --query "BTC和ETH的策略对比" \
#   --coins "BTC,ETH" \
#   --top-per-group 2 \
#   --min-stability 0.5 \
#   --max-combinations 3

echo ""
echo "✅ 测试完成"
