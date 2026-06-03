#!/usr/bin/env python3
"""查询用户绑定的交易所账户列表"""
from typing import Optional

from api_client import api_post, check_auth, BASE_URL

EXCHANGE_STATUS_MAP = {
    "1": "未连接",
    "2": "已连接",
}


def run(
    token: str,
    page: int = 1,
    limit: int = -1,
    agent_id: Optional[str] = None,
) -> dict:
    """
    查询交易所账户列表。

    Returns:
        {"status": "ok"|"error", "total": int, "exchanges": [...], "filters": {...}}
    """
    data = api_post(
        "/User/exchange_lists",
        {
            "page": page,
            "limit": limit,
            "usertoken": token,
            "app_v": "2.0.0",
            "lang": 1,
        },
        agent_id,
    )
    ok, msg = check_auth(data)
    if not ok:
        return {"status": "error", "message": msg}

    if data.get("status") != 1:
        return {"status": "error", "message": data.get("msg", "未知错误"), "raw": data}

    exchanges_raw = data.get("info", [])
    all_count = int(data.get("url", {}).get("all_count", len(exchanges_raw)))

    exchanges = []
    for e in exchanges_raw:
        status_val = str(e.get("status", ""))
        exchanges.append({
            "id": e.get("id"),
            "exchange_name": e.get("exchange_name"),
            "name": e.get("name"),
            "status": e.get("status"),
            "status_label": EXCHANGE_STATUS_MAP.get(status_val, f"未知({status_val})"),
            "is_connected": status_val == "2",
        })

    return {
        "status": "ok",
        "total": all_count,
        "page": page,
        "limit": limit,
        "exchanges": exchanges,
    }