#!/usr/bin/env python3
"""查询用户绑定的交易所账户列表"""
import sys
import os
import requests
from typing import Optional

# 日志模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts', 'logging'))
from api_logger import log_http_request, log_error

BASE_URL = "https://www.fourieralpha.com/Mobile"

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
    params = {
        "page": page,
        "limit": limit,
        "usertoken": token,
        "app_v": "2.0.0",
        "lang": 1,
    }

    url = f"{BASE_URL}/User/exchange_lists"

    try:
        resp = requests.post(url, data=params, timeout=30)
        data = resp.json()
        log_http_request(url, params, response=data, agent_id=agent_id)

        if data.get("status") != 1:
            msg = data.get("msg", "未知错误")
            return {"status": "error", "message": msg, "raw": data}

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

    except requests.RequestException as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"status": "error", "message": f"网络请求异常: {str(e)}"}
    except Exception as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"status": "error", "message": f"脚本异常: {str(e)}"}