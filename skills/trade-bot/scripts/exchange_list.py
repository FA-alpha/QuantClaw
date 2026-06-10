#!/usr/bin/env python3
"""查询用户绑定的交易所账户列表 — 薄包装，委托 platform_data"""
from typing import Optional

from platform_data import get_exchange_list


def run(
    token: str,
    page: int = 1,
    limit: int = -1,
    agent_id: Optional[str] = None,
) -> dict:
    """委托 platform_data.get_exchange_list()"""
    return get_exchange_list(token=token, page=page, limit=limit, agent_id=agent_id)
