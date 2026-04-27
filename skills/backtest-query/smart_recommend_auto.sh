#!/bin/bash
# 智能推荐包装脚本 - 自动获取 token
# 用法: ./smart_recommend_auto.sh --coins "BTC,ETH" --year 2024 [其他参数]

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 自动获取 token
echo "🔑 获取用户 token..." >&2
USER_TOKEN=$(python3 "$SCRIPT_DIR/get_token.py")

if [ $? -ne 0 ] || [ -z "$USER_TOKEN" ]; then
  echo "❌ 获取 token 失败" >&2
  exit 1
fi

echo "✅ Token 获取成功" >&2

# 调用真实的脚本，传递所有参数
python3 "$SCRIPT_DIR/smart_recommend.py" --token "$USER_TOKEN" --workspace "$(pwd)" "$@"
