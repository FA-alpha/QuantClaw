#!/usr/bin/env python3
"""
查询 FourierAlpha 策略列表
"""

import json
import sys
import requests
import os

# 读取 token
script_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(script_dir, '../users.json'), 'r') as f:
    config = json.load(f)
    token = config['fourieralpha']['usertoken']

# 查询策略列表
url = "https://www.fourieralpha.com/Mobile/Strategy/lists"
data = {
    "usertoken": token,
    "page": "1",
    "limit": "100"
}

resp = requests.post(url, data=data, timeout=60)
result = resp.json()

if result.get("status") != 1:
    print(f"错误: {result.get('info')}")
    sys.exit(1)

info = result.get('info', [])
print(f"总策略数: {len(info)}\n")
print("策略列表:")
print("-" * 80)

for s in info:
    print(f"ID: {s.get('id')}")
    print(f"名称: {s.get('name')}")
    print(f"币种: {s.get('coin')} | 方向: {s.get('direction')}")
    print(f"类型: {'现货' if s.get('amt_type') == '1' else '合约'}")
    print()
