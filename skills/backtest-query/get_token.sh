#!/bin/bash
# 获取当前 Agent 的 token
# 用法: ./get_token.sh

# 从 workspace 路径提取 agentId
WORKSPACE=$(pwd)
AGENT_ID=$(basename "$WORKSPACE" | sed 's/clawd-//')

# 调用 Gateway RPC 获取 token
RESPONSE=$(curl -s -X POST http://127.0.0.1:18789/api/rpc \
  -H "Content-Type: application/json" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"id\": 1,
    \"method\": \"quantclaw.getMyToken\",
    \"params\": {
      \"agentId\": \"$AGENT_ID\"
    }
  }")

# 解析响应
if echo "$RESPONSE" | jq -e '.result.token' > /dev/null 2>&1; then
  TOKEN=$(echo "$RESPONSE" | jq -r '.result.token')
  echo "$TOKEN"
  exit 0
else
  ERROR=$(echo "$RESPONSE" | jq -r '.error.message // .result.error // "Unknown error"')
  echo "Error: $ERROR" >&2
  exit 1
fi
