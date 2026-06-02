#!/usr/bin/env python3
"""
平台公共数据模块 — fourieralpha 平台级数据查询

币种/策略/时间等平台参考数据带 24h 磁盘缓存；
交易所列表不缓存（账户状态可能变化）。
"""
import sys
import os
import json
import time
import requests
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.logging import log_http_request, log_error

BASE_URL = "https://www.fourieralpha.com/Mobile"
CACHE_DIR = os.path.expanduser("~/.quantclaw/cache")
CACHE_TTL_S = 86400  # 24 小时


# ── 缓存工具 ──────────────────────────────────────────────────

def _cache_path(key: str) -> str:
    """key → ~/.quantclaw/cache/platform/<key>.json"""
    return os.path.join(CACHE_DIR, f"{key}.json")


def _cache_read(key: str) -> Optional[dict]:
    """读缓存，过期返回 None"""
    p = _cache_path(key)
    if not os.path.exists(p):
        return None
    try:
        with open(p) as f:
            entry = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None
    if time.time() - entry.get("ts", 0) > CACHE_TTL_S:
        return None
    return entry.get("data")


def _cache_write(key: str, data: dict) -> None:
    """写缓存"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    entry = {"ts": time.time(), "data": data}
    with open(_cache_path(key), "w") as f:
        json.dump(entry, f)


def _clear_cache(key: str) -> None:
    """删单个缓存文件"""
    p = _cache_path(key)
    if os.path.exists(p):
        os.remove(p)


# ── 内部请求封装 ──────────────────────────────────────────────

def _post(api_path: str, params: dict, agent_id: Optional[str] = None) -> dict:
    """通用 POST，返回 API 原始 dict。鉴权失败/网络异常抛出的信息统一包装在返回值中。"""
    url = f"{BASE_URL}{api_path}"
    try:
        resp = requests.post(url, data=params, timeout=30)
        data = resp.json()
        log_http_request(url, params, response=data, agent_id=agent_id)
        return data
    except requests.RequestException as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"_error": f"网络请求异常: {str(e)}"}
    except Exception as e:
        log_error(str(e), exception=e, context={"url": url}, agent_id=agent_id)
        return {"_error": f"脚本异常: {str(e)}"}


def _check_auth(data: dict) -> tuple:
    """检查 API 鉴权状态。返回 (ok, message)"""
    if data.get("_error"):
        return False, data["_error"]
    if data.get("status") == 0:
        info = data.get("info", "未知错误")
        info_str = str(info)
        if "Column not found" in info_str and "version" in info_str:
            return True, ""
        return False, info_str
    return True, ""


# ── 缓存辅助：只缓存 platform reference data ─────────────────

def _cached_fetch(
    cache_key: str,
    api_path: str,
    params: dict,
    parser: callable,
    agent_id: Optional[str] = None,
) -> dict:
    """缓存优先：命中 → 直接返回；未命中 → 调 API → 写缓存 → 返回"""
    cached = _cache_read(cache_key)
    if cached is not None:
        return cached

    data = _post(api_path, params, agent_id)
    ok, msg = _check_auth(data)
    if not ok:
        return {"status": "error", "message": msg}

    result = parser(data)
    _cache_write(cache_key, result)
    return result


# ═══════════════════════════════════════════════════════════════
# 币种
# ═══════════════════════════════════════════════════════════════

def _parse_coin_list(data: dict) -> dict:
    coins = []
    for item in data.get("info", []):
        coins.append({
            "coin": item.get("coin"),
            "name": item.get("name"),
            "type": item.get("type"),
        })
    return {"status": "ok", "total": len(coins), "coins": coins}


def get_coin_list(
    token: str,
    agent_id: Optional[str] = None,
) -> dict:
    """获取可用币种列表（24h 缓存）。API: /Strategy/coin_lists"""
    return _cached_fetch(
        cache_key="coins",
        api_path="/Strategy/coin_lists",
        params={"usertoken": token, "app_v": "2.0.0"},
        parser=_parse_coin_list,
        agent_id=agent_id,
    )


# ═══════════════════════════════════════════════════════════════
# 时间
# ═══════════════════════════════════════════════════════════════

def _parse_ai_time_list(data: dict) -> dict:
    times = []
    for item in data.get("info", []):
        times.append({"id": item.get("id"), "name": item.get("name")})
    return {"status": "ok", "total": len(times), "times": times}


def get_ai_time_list(
    token: str,
    agent_id: Optional[str] = None,
) -> dict:
    """获取 AI 回测时间列表（24h 缓存）。API: /Extend/ai_time_lists"""
    return _cached_fetch(
        cache_key="ai_times",
        api_path="/Extend/ai_time_lists",
        params={"usertoken": token, "app_v": "2.0.0"},
        parser=_parse_ai_time_list,
        agent_id=agent_id,
    )


# ═══════════════════════════════════════════════════════════════
# 策略
# ═══════════════════════════════════════════════════════════════

def _parse_ai_strategy_list(data: dict) -> dict:
    strategies = []
    for item in data.get("info", []):
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
    return {"status": "ok", "total": len(strategies), "strategies": strategies}


def get_ai_strategy_list(
    token: str,
    agent_id: Optional[str] = None,
) -> dict:
    """获取 AI 策略类型列表（24h 缓存）。API: /Extend/ai_strategy_lists"""
    return _cached_fetch(
        cache_key="ai_strategies",
        api_path="/Extend/ai_strategy_lists",
        params={"usertoken": token, "app_v": "2.0.0"},
        parser=_parse_ai_strategy_list,
        agent_id=agent_id,
    )


# ═══════════════════════════════════════════════════════════════
# 交易所（不缓存）
# ═══════════════════════════════════════════════════════════════

def get_exchange_list(
    token: str,
    page: int = 1,
    limit: int = -1,
    agent_id: Optional[str] = None,
) -> dict:
    """获取交易所账户列表（不缓存）。API: /User/exchange_lists"""
    data = _post(
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
    ok, msg = _check_auth(data)
    if not ok:
        return {"status": "error", "message": msg}

    if data.get("status") != 1:
        return {"status": "error", "message": data.get("msg", "未知错误"), "raw": data}

    EXCHANGE_STATUS_MAP = {"1": "未连接", "2": "已连接"}
    exchanges_raw = data.get("info", [])
    all_count = int(data.get("url", {}).get("all_count", len(exchanges_raw)))

    exchanges = []
    for e in exchanges_raw:
        sv = str(e.get("status", ""))
        exchanges.append({
            "id": e.get("id"),
            "exchange_name": e.get("exchange_name"),
            "name": e.get("name"),
            "status": e.get("status"),
            "status_label": EXCHANGE_STATUS_MAP.get(sv, f"未知({sv})"),
            "is_connected": sv == "2",
        })

    return {
        "status": "ok",
        "total": all_count,
        "page": page,
        "limit": limit,
        "exchanges": exchanges,
    }