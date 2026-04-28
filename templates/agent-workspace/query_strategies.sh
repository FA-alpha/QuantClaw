#!/bin/bash
# 查询 FourierAlpha 策略列表

TOKEN=$(cat users.json | jq -r '.fourieralpha.usertoken')

curl -s -X POST "https://www.fourieralpha.com/Mobile/Strategy/lists" \
  -d "usertoken=$TOKEN" \
  -d "page=1" \
  -d "limit=100" | python3 -c "
import json, sys
data = json.load(sys.stdin)
info = data.get('info', [])

print(f'总策略数: {len(info)}\n')
print('策略列表:')
print('-' * 80)

for s in info:
    print(f\"ID: {s.get('id')}\")
    print(f\"名称: {s.get('name')}\")
    print(f\"币种: {s.get('coin')} | 方向: {s.get('direction')}\")
    print(f\"类型: {s.get('amt_type')} (现货/合约)\")
    print()
"
