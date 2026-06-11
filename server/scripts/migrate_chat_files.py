#!/usr/bin/env python3
"""
一键迁移旧格式聊天文件 -> 新格式

旧格式: {user_id}.json   (例如 u_abc123.json)
新格式: {user_id}__{safe_session_key}.json

session_key = agent:{agent_id}:main
safe 规则: ':' -> '_', '-' -> '_'

用法:
    python3 migrate_chat_files.py /home/node/quantclaw/server/data-docker/chats /path/to/users.json
"""

import json
import sys
from pathlib import Path


def safe_key(session_key: str) -> str:
    """agent:qc-xxx:main -> agent_qc_xxx_main"""
    return session_key.replace(':', '_').replace('-', '_')


def migrate(chats_dir: Path, users_file: Path) -> int:
    """迁移旧格式聊天文件，返回迁移数量"""
    if not users_file.exists():
        print(f"[ERR] users.json not found: {users_file}")
        return 0

    users = json.loads(users_file.read_text())

    # 构建 user_id -> agent_id 映射
    uid_to_agent = {}
    for key, user in users.items():
        uid = user.get('userId')
        aid = user.get('agentId')
        if uid and aid:
            uid_to_agent[uid] = aid

    if not uid_to_agent:
        print("[WARN] No user_id->agent_id mapping found in users.json, nothing to migrate")
        return 0

    count = 0
    for old_file in chats_dir.glob('*.json'):
        name = old_file.stem

        # 跳过已经是新格式的、备份文件、已迁移标记
        if '__' in name or name.endswith('.bak') or name.endswith('.migrated'):
            continue

        user_id = name
        agent_id = uid_to_agent.get(user_id)

        if not agent_id:
            print(f"[SKIP] {old_file.name}: user_id={user_id} not found in users.json")
            continue

        # 构造新文件名
        session_key = f'agent:{agent_id}:main'
        safe = safe_key(session_key)
        new_file = chats_dir / f'{user_id}__{safe}.json'

        try:
            data = json.loads(old_file.read_text())
            new_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            old_file.rename(old_file.with_suffix('.json.migrated'))
            print(f"[OK] {old_file.name} -> {new_file.name}")
            count += 1
        except Exception as e:
            print(f"[ERR] {old_file.name}: {e}")

    return count


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <chats_dir> <users.json>")
        print(f"Example: {sys.argv[0]} /home/node/quantclaw/server/data-docker/chats /home/node/.quantclaw/users/users.json")
        sys.exit(1)

    chats_dir = Path(sys.argv[1])
    users_file = Path(sys.argv[2])
    n = migrate(chats_dir, users_file)
    print(f"\n✅ Done. Migrated {n} file(s).")
