#!/usr/bin/env python3
"""查询用户绑定的交易所账户列表（薄封装，核心逻辑在 scripts/api_client.py）"""
import sys
import os
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from scripts.api_client import get_exchange_list as _api_get_exchange_list


def run(
    token: str,
    page: int = 1,
    limit: int = -1,
    agent_id: Optional[str] = None,
) -> dict:
    return _api_get_exchange_list(token=token, page=page, limit=limit, agent_id=agent_id)