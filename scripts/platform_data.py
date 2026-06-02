#!/usr/bin/env python3
"""
平台公共数据模块 — fourieralpha 平台级数据查询（不缓存，实时获取）

提供策略类型、交易所列表等平台公共数据的查询函数，
各 skill 脚本按需调用，避免重复实现。
"""
import sys
import os
import requests
from typing import Optional

# 确保可以导入同级的 logging 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.logging import log_http_request, log_error

BASE_URL = "https://www.fourieralpha.com/Mobile"


def _check_auth(data: dict) -> tuple:
    """检查 API 鉴权状态。返回 (ok, message/empty)"""
    if data.get("status") == 0:
        info = data.get("info", "未知错误")
        info_str = str(info)
        if "Column not found" in info_str and "version" in info_str:
            return True, "[]"
        return False, info_str
    return True, ""


# ═══════════════════════════════════════════════════════════════
# 币种相关
# ═══════════════════════════════════════════════════════════════

def get_coin_list(
    token: str,
    agent_id: Optional[str] = None,
) -> dict:
    """
    获取可用币种列表（实时，不缓存）。

    API: POST /Strategy/coin_lists

    Returns:
        {"status": "ok", "total": int, "coins": [...]}
        or {"status": "error", "message": "..."}
    """
    url = f"{BASE_URL}/Strategy/coin_lists"
    params = {"usertoken": token, "app_v": "2.0.0"}

    try:
        resp = requests.post(url, data=params, timeout=30)
        data = resp.json()
        log_http_request(url, params, response=data, agent_id=agent_id)

        ok, msg = _check_auth(data)
        if not ok:
            return {"status": "error", "message": msg, "raw": data}

        coins_raw = data.get("info", [])
        coins = []
        for item in coins_raw:
            coins.append({
                "coin": item.get("coin"),
                "name": item.get("name"),
                "type": item.get("type"),
            })

        return {
            "status": "ok",
            "total": len(coins),
            "coins": coins,
        }

    except requests.RequestException as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"status": "error", "message": f"网络请求异常: {str(e)}"}
    except Exception as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"status": "error", "message": f"脚本异常: {str(e)}"}


# ═══════════════════════════════════════════════════════════════
# 时间相关
# ═══════════════════════════════════════════════════════════════

def get_ai_time_list(
    token: str,
    agent_id: Optional[str] = None,
) -> dict:
    """
    获取 AI 回测时间列表（实时，不缓存）。

    API: POST /Extend/ai_time_lists

    Returns:
        {"status": "ok", "total": int, "times": [...]}
        or {"status": "error", "message": "..."}
    """
    url = f"{BASE_URL}/Extend/ai_time_lists"
    params = {"usertoken": token, "app_v": "2.0.0"}

    try:
        resp = requests.post(url, data=params, timeout=30)
        data = resp.json()
        log_http_request(url, params, response=data, agent_id=agent_id)

        ok, msg = _check_auth(data)
        if not ok:
            return {"status": "error", "message": msg, "raw": data}

        times_raw = data.get("info", [])
        times = []
        for item in times_raw:
            times.append({
                "id": item.get("id"),
                "name": item.get("name"),
            })

        return {
            "status": "ok",
            "total": len(times),
            "times": times,
        }

    except requests.RequestException as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"status": "error", "message": f"网络请求异常: {str(e)}"}
    except Exception as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"status": "error", "message": f"脚本异常: {str(e)}"}


# ═══════════════════════════════════════════════════════════════
# 策略相关
# ═══════════════════════════════════════════════════════════════

def get_ai_strategy_list(
    token: str,
    agent_id: Optional[str] = None,
) -> dict:
    """
    获取 AI 策略类型列表（实时，不缓存）。

    API: POST /Extend/ai_strategy_lists

    Returns:
        {"status": "ok", "strategies": [...], "total": int}
        or {"status": "error", "message": "..."}
    """
    url = f"{BASE_URL}/Extend/ai_strategy_lists"
    params = {"usertoken": token, "app_v": "2.0.0"}

    try:
        resp = requests.post(url, data=params, timeout=30)
        data = resp.json()
        log_http_request(url, params, response=data, agent_id=agent_id)

        ok, msg = _check_auth(data)
        if not ok:
            return {"status": "error", "message": msg, "raw": data}

        strategies_raw = data.get("info", [])
        strategies = []
        for item in strategies_raw:
            strategies.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "strategy_type": item.get("strategy_type"),
                "versions": [
                    {
                        "id": v.get("id"),
                        "name": v.get("name"),
                        "version": v.get("version"),
                        "leverage": v.get("leverage"),
                    }
                    for v in item.get("versions", [])
                ],
            })

        return {
            "status": "ok",
            "total": len(strategies),
            "strategies": strategies,
        }

    except requests.RequestException as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"status": "error", "message": f"网络请求异常: {str(e)}"}
    except Exception as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"status": "error", "message": f"脚本异常: {str(e)}"}


# ═══════════════════════════════════════════════════════════════
# 交易所相关
# ═══════════════════════════════════════════════════════════════

def get_exchange_list(
    token: str,
    page: int = 1,
    limit: int = -1,
    agent_id: Optional[str] = None,
) -> dict:
    """
    获取交易所账户列表（实时，不缓存）。

    API: POST /User/exchange_lists

    Returns:
        {"status": "ok", "total": int, "exchanges": [...]}
    """
    url = f"{BASE_URL}/User/exchange_lists"
    params = {
        "page": page,
        "limit": limit,
        "usertoken": token,
        "app_v": "2.0.0",
        "lang": 1,
    }

    try:
        resp = requests.post(url, data=params, timeout=30)
        data = resp.json()
        log_http_request(url, params, response=data, agent_id=agent_id)

        if data.get("status") != 1:
            return {"status": "error", "message": data.get("msg", "未知错误"), "raw": data}

        exchanges_raw = data.get("info", [])
        all_count = int(data.get("url", {}).get("all_count", len(exchanges_raw)))

        EXCHANGE_STATUS_MAP = {"1": "未连接", "2": "已连接"}
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