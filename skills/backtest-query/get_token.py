#!/usr/bin/env python3
"""
获取当前 Agent 的 token
用法: python get_token.py
"""

import os
import sys
import json

def get_agent_token():
    """从 workspace 路径和 users.json 获取 token"""
    
    # 1. 从当前路径提取 agentId
    workspace = os.getcwd()
    agent_id = os.path.basename(workspace).replace('clawd-', '')
    
    # 2. 读取 users.json
    users_file = os.path.expanduser('~/.quantclaw/users.json')
    
    if not os.path.exists(users_file):
        print(f"Error: {users_file} not found", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(users_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {users_file}: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 3. 查找对应的用户
    users = data.get('users', [])
    for user in users:
        if user.get('agentId') == agent_id:
            token = user.get('token')
            if token:
                print(token)
                sys.exit(0)
            else:
                print("Error: Token not found for this agent", file=sys.stderr)
                sys.exit(1)
    
    print(f"Error: Agent {agent_id} not found in users database", file=sys.stderr)
    sys.exit(1)

if __name__ == '__main__':
    get_agent_token()
