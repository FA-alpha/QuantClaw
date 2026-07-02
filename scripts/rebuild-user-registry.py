#!/usr/bin/env python3
"""
从 users.json 恢复 user_registry.json

用法：
  python3 scripts/rebuild-user-registry.py <users.json> [output.json]

默认输出到 users.json 同目录下的 user_registry.json。
"""

import json
import os
import sys


def rebuild(in_path: str, out_path: str = None) -> dict:
    if not os.path.exists(in_path):
        print(f"❌ 文件不存在: {in_path}")
        sys.exit(1)

    data = json.load(open(in_path))
    users = data.get("users", data) if isinstance(data, dict) else data

    registry = {}
    for u in users:
        agent_id = u.get("agentId")
        user_id = u.get("userId")
        if agent_id and user_id:
            registry[agent_id] = user_id

    if out_path is None:
        out_path = os.path.join(os.path.dirname(in_path) or ".", "user_registry.json")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)

    print(f"✅ 已从 {in_path} 生成 {out_path}")
    for k, v in registry.items():
        print(f"   {k} -> {v}")
    print(f"   共 {len(registry)} 个用户")
    return registry


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 rebuild-user-registry.py <users.json> [output.json]")
        sys.exit(1)
    rebuild(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
