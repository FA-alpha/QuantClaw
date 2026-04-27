#!/bin/bash
# 智能推荐技能测试脚本

set -e  # 遇到错误立即退出

echo "======================================"
echo "智能推荐技能测试"
echo "======================================"
echo ""

# 检查参数
if [ -z "$1" ]; then
    echo "❌ 错误: 需要提供 token"
    echo ""
    echo "用法: $0 <token> [workspace]"
    echo ""
    echo "示例:"
    echo "  $0 qc_abc123"
    echo "  $0 qc_abc123 /home/ubuntu/quantclaw"
    exit 1
fi

TOKEN="$1"
WORKSPACE="${2:-/home/ubuntu/quantclaw}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "📝 配置信息:"
echo "   Token: ${TOKEN:0:10}..."
echo "   Workspace: $WORKSPACE"
echo "   Script: $SCRIPT_DIR"
echo ""

# ====================================
# 测试 1: 基础查询（快速测试 API 连通性）
# ====================================
echo "======================================"
echo "测试 1: 基础查询"
echo "======================================"
echo ""

echo "🔍 查询可用币种..."
python3 "$SCRIPT_DIR/query.py" --token "$TOKEN" --list-coins 2>&1 | head -20
echo ""

echo "🔍 查询可用策略类型..."
python3 "$SCRIPT_DIR/query.py" --token "$TOKEN" --list-strategies 2>&1 | head -20
echo ""

echo "✅ 测试 1 完成"
echo ""

# ====================================
# 测试 2: 快速智能推荐（不获取详情）
# ====================================
echo "======================================"
echo "测试 2: 快速智能推荐（探索模式）"
echo "======================================"
echo ""
echo "参数配置:"
echo "  - 币种: 自动（BTC/ETH/SOL）"
echo "  - 策略类型: 自动（风霆/网格/鲲鹏）"
echo "  - 时间: 最近1年"
echo "  - 模式: 快速（不获取详情）"
echo ""

python3 "$SCRIPT_DIR/smart_recommend.py" \
    --token "$TOKEN" \
    --group-size 2 \
    --top-n 2 \
    --no-detail \
    --format text

echo ""
echo "✅ 测试 2 完成"
echo ""

# ====================================
# 测试 3: 指定币种推荐
# ====================================
echo "======================================"
echo "测试 3: 指定币种推荐"
echo "======================================"
echo ""
echo "参数配置:"
echo "  - 币种: BTC"
echo "  - 策略类型: 自动"
echo "  - 时间: 2024年"
echo "  - 模式: 快速"
echo ""

python3 "$SCRIPT_DIR/smart_recommend.py" \
    --token "$TOKEN" \
    --coins "BTC" \
    --year 2024 \
    --group-size 2 \
    --top-n 2 \
    --no-detail \
    --format text

echo ""
echo "✅ 测试 3 完成"
echo ""

# ====================================
# 测试 4: 完整推荐（获取详情）
# ====================================
echo "======================================"
echo "测试 4: 完整推荐（含详情和记忆）"
echo "======================================"
echo ""
echo "⚠️  此测试较慢，需要获取策略详情..."
echo ""
echo "参数配置:"
echo "  - 币种: BTC, ETH"
echo "  - 策略类型: 风霆(11)"
echo "  - 时间: 2024年"
echo "  - 筛选: 夏普≥1.5, 回撤≤20%"
echo "  - 组合: 3个策略，返回前3个推荐"
echo "  - 保存: 到记忆"
echo ""

python3 "$SCRIPT_DIR/smart_recommend.py" \
    --token "$TOKEN" \
    --coins "BTC,ETH" \
    --strategy-type 11 \
    --year 2024 \
    --min-sharpe 1.5 \
    --max-drawdown 20 \
    --group-size 3 \
    --top-n 3 \
    --workspace "$WORKSPACE" \
    --save-memory

echo ""
echo "✅ 测试 4 完成"
echo ""

# ====================================
# 测试 5: JSON 输出格式
# ====================================
echo "======================================"
echo "测试 5: JSON 输出格式"
echo "======================================"
echo ""
echo "用于程序调用的 JSON 格式输出..."
echo ""

python3 "$SCRIPT_DIR/smart_recommend.py" \
    --token "$TOKEN" \
    --coins "BTC" \
    --year 2024 \
    --group-size 2 \
    --top-n 1 \
    --no-detail \
    --format json \
    --quiet

echo ""
echo "✅ 测试 5 完成"
echo ""

# ====================================
# 测试完成
# ====================================
echo "======================================"
echo "🎉 所有测试完成！"
echo "======================================"
echo ""
echo "📊 测试总结:"
echo "  ✅ 测试 1: 基础查询"
echo "  ✅ 测试 2: 快速推荐（探索模式）"
echo "  ✅ 测试 3: 指定币种推荐"
echo "  ✅ 测试 4: 完整推荐（含详情）"
echo "  ✅ 测试 5: JSON 格式输出"
echo ""
echo "📝 查看记忆:"
echo "  cat $WORKSPACE/memory/portfolio_history.md"
echo ""
