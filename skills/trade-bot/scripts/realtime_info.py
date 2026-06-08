#!/usr/bin/env python3
"""
实时数据查询 — /Stat/realtime_info

获取最新币价、可用余额等实时数据。
手动加仓前需要用此接口辅助决策。
"""
import time
from typing import Optional

from api_client import api_post, check_auth


def _get_cached_info(bot_id: str) -> Optional[dict]:
    """读详情缓存，取 trade_token + coin"""
    import json, os
    cache_path = f"/tmp/quantclaw/bot_details/{bot_id}.json"
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path) as f:
            return json.load(f)
    except Exception:
        return None


def run(
    token: str,
    bot_id: str,
    show_type: str = "1,2",
    agent_id: Optional[str] = None,
) -> dict:
    """
    查询实时数据。

    Args:
        token: 用户 token
        bot_id: 机器人 ID
        show_type: 数据类型，逗号分隔。1=最新币价 2=可用余额 3=可减少保证金
        agent_id: Agent ID

    Returns:
        {
            "status": "ok" | "error",
            "timestamp": <Unix秒>,
            "timestamp_label": "2026-06-04 18:15:30",
            "items": [
                {"type": "1", "type_label": "最新币价", "amt": 75200.5, "coin": "BTC"},
                {"type": "2", "type_label": "可用余额", "amt": 500.0, "coin": "USDT"},
            ]
        }
    """
    info = _get_cached_info(bot_id)
    if not info:
        # 缓存缺失，自动调 detail 填充
        from detail_bot import run as detail_run
        dr = detail_run(token=token, bot_id=bot_id, agent_id=agent_id)
        if dr.get("status") != "ok":
            return {"status": "error", "message": "详情查询失败，无法获取实时数据"}
        info = _get_cached_info(bot_id)
        if not info:
            return {"status": "error", "message": "详情缓存写入失败"}

    trade_info = info.get("trade_info", {})
    trade_token = trade_info.get("trade_token", "")
    if not trade_token:
        return {"status": "error", "message": "trade_token 缺失，无法查询实时数据"}

    strategy_rule = info.get("strategy_rule", {})
    coin = strategy_rule.get("coin", "")

    now = time.time()

    data = api_post(
        "/Stat/realtime_info",
        {
            "usertoken": token,
            "app_v": "2.0.0",
            "trade_token": trade_token,
            "show_type": show_type,
            "coin": coin,
        },
        agent_id,
    )
    ok, msg = check_auth(data)
    if not ok:
        return {"status": "error", "message": msg}

    if data.get("status") != 1:
        return {"status": "error", "message": data.get("msg", data.get("info", "未知错误"))}

    TYPE_LABEL = {"1": "最新币价", "2": "可用余额", "3": "可减少保证金"}
    raw = data.get("info", [])
    items = []
    for item in (raw if isinstance(raw, list) else []):
        t = str(item.get("type", ""))
        items.append({
            "type": t,
            "type_label": TYPE_LABEL.get(t, f"未知({t})"),
            "amt": item.get("amt"),
            "coin": item.get("coin", coin),
        })

    return {
        "status": "ok",
        "timestamp": int(now),
        "timestamp_label": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "items": items,
    }